from typing import Optional
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    NestedStack,
)
from constructs import Construct

from zen_safe.postgres_construct import PostgresDatabaseConstruct
from zen_safe.rabbitmq_construct import RabbitMQConstruct
from zen_safe.safe_shared_stack import SafeSharedStack
from zen_safe.redis_construct import RedisConstruct


class SafeTransactionStack(NestedStack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        shared_stack: SafeSharedStack,
        events_mq: RabbitMQConstruct,
        alb: elbv2.IApplicationLoadBalancer,
        chain_name: str,
        number_of_workers: int = 2,
        cache_node_type: str = "cache.t3.small",
        mq_node_type: str = "mq.t3.small",
        ssl_certificate_arn: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        formatted_chain_name = chain_name.upper()

        ecs_cluster = ecs.Cluster(
            self,
            "SafeCluster",
            enable_fargate_capacity_providers=True,
            vpc=vpc,
        )

        # Tx cache
        self._tx_redis_cluster_mainnet = RedisConstruct(
            self,
            "RedisCluster",
            vpc=vpc,
            cache_node_type=cache_node_type
        )

        # Tx queue
        self._tx_rabbit_mq = RabbitMQConstruct(self, "TxRabbitMQ", vpc=vpc, mq_node_type=mq_node_type)

        # Tx db
        self._tx_database = PostgresDatabaseConstruct(self, "TxDatabaseMainnet", vpc=vpc)

        container_args = {
            "image": ecs.ContainerImage.from_asset("docker/transactions"),
            "environment": {
                "PYTHONPATH": "/app/",
                "DJANGO_SETTINGS_MODULE": "config.settings.production",
                "C_FORCE_ROOT": "true",
                "DEBUG": "0",
                "ETH_L2_NETWORK": "0",
                "EVENTS_QUEUE_ASYNC_CONNECTION":"True",
                "EVENTS_QUEUE_EXCHANGE_NAME": "safe-transaction-service-events",
                "DJANGO_ALLOWED_HOSTS": "*",
                "DB_MAX_CONNS": "15",
                "ETH_INTERNAL_TXS_BLOCK_PROCESS_LIMIT": "5000",
                "FORCE_SCRIPT_NAME": "/txs/",
                "CSRF_TRUSTED_ORIGINS": "https://safe.zenchain.io",
                "WORKER_QUEUES": "default,indexing,processing,contracts,tokens,notifications,webhooks"
            },
            "secrets": {
                "DJANGO_SECRET_KEY": ecs.Secret.from_secrets_manager(
                    shared_stack.secrets, f"TX_DJANGO_SECRET_KEY_{formatted_chain_name}"
                ),
                "DATABASE_URL": ecs.Secret.from_secrets_manager(self._tx_database.connection_string_secret),
                "CELERY_BROKER_URL": ecs.Secret.from_secrets_manager(self._tx_redis_cluster_mainnet.connection_string_secret),
                "EVENTS_QUEUE_URL": ecs.Secret.from_secrets_manager(events_mq.connection_string_secret),
                "REDIS_URL": ecs.Secret.from_secrets_manager(self._tx_redis_cluster_mainnet.connection_string_secret),
                "ETHEREUM_NODE_URL": ecs.Secret.from_secrets_manager(
                    shared_stack.secrets, f"TX_ETHEREUM_NODE_URL_{formatted_chain_name}"
                ),
                "ETHEREUM_TRACING_NODE_URL": ecs.Secret.from_secrets_manager(
                    shared_stack.secrets,
                    f"TX_ETHEREUM_TRACING_NODE_URL_{formatted_chain_name}",
                ),
                "ETHERSCAN_API_KEY": ecs.Secret.from_secrets_manager(
                    shared_stack.secrets,
                    f"TX_ETHERSCAN_API_KEY_{formatted_chain_name}",
                ),
            },
        }

        ## Web
        web_task_definition = ecs.FargateTaskDefinition(
            self,
            "SafeTransactionServiceWeb",
            cpu=512,
            memory_limit_mib=1024,
            family="SafeServices",
            volumes=[
                ecs.Volume(
                    name="nginx_volume",
                )
            ],
        )

        web_container = web_task_definition.add_container(
            "Web",
            container_name="web",
            working_directory="/app",
            command=["/app/run_web.sh"],
            logging=ecs.AwsLogDriver(
                log_group=shared_stack.log_group,
                stream_prefix="Web",
                mode=ecs.AwsLogDriverMode.NON_BLOCKING,
            ),
            port_mappings=[ecs.PortMapping(container_port=8888)],
            **container_args,
        )

        web_container.add_mount_points(
            ecs.MountPoint(
                source_volume="nginx_volume",
                container_path="/app/staticfiles",
                read_only=False,
            )
        )

        nginx_container = web_task_definition.add_container(
            "StaticFiles",
            container_name="static",
            image=ecs.ContainerImage.from_registry("nginx:latest"),
            port_mappings=[ecs.PortMapping(container_port=80)],
        )

        nginx_container.add_mount_points(
            ecs.MountPoint(
                source_volume="nginx_volume",
                container_path="/usr/share/nginx/html/static",
                read_only=True,
            )
        )

        web_service = ecs.FargateService(
            self,
            "WebService",
            cluster=ecs_cluster,
            task_definition=web_task_definition,
            desired_count=1,
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            enable_execute_command=True,
        )

        ## Worker
        worker_task_definition = ecs.FargateTaskDefinition(
            self,
            "SafeTransactionServiceWorker",
            cpu=512,
            memory_limit_mib=1024,
            family="SafeServices",
        )

        worker_task_definition.add_container(
            "Worker",
            container_name="worker",
            command=["docker/web/celery/worker/run.sh"],
            logging=ecs.AwsLogDriver(
                log_group=shared_stack.log_group,
                stream_prefix="Worker",
                mode=ecs.AwsLogDriverMode.NON_BLOCKING,
            ),
            **container_args,
        )

        worker_service = ecs.FargateService(
            self,
            "WorkerService",
            cluster=ecs_cluster,
            task_definition=worker_task_definition,
            desired_count=number_of_workers,
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
        )

        ## Scheduled Tasks
        schedule_task_definition = ecs.FargateTaskDefinition(
            self,
            "SafeTransactionServiceSchedule",
            cpu=512,
            memory_limit_mib=1024,
            family="SafeServices",
        )

        schedule_task_definition.add_container(
            "Schedule",
            container_name="schedule",
            command=["docker/web/celery/scheduler/run.sh"],
            logging=ecs.AwsLogDriver(
                log_group=shared_stack.log_group,
                stream_prefix="schedule",
                mode=ecs.AwsLogDriverMode.NON_BLOCKING,
            ),
            **container_args,
        )

        schedule_service = ecs.FargateService(
            self,
            "ScheduleService",
            cluster=ecs_cluster,
            task_definition=schedule_task_definition,
            desired_count=1,
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
        )

        ## Setup LB and redirect traffic to web and static containers

        listener = alb.add_listener("Listener", port=80)

        listener.add_targets(
            "Static",
            port=80,
            targets=[web_service.load_balancer_target(container_name="static")],
            priority=1,
            conditions=[elbv2.ListenerCondition.path_patterns(["/static/*"])],
            health_check=elbv2.HealthCheck(path="/static/drf-yasg/style.css"),
        )
        listener.add_targets(
            "WebTarget",
            port=80,
            targets=[web_service.load_balancer_target(container_name="web")],
        )

        if ssl_certificate_arn is not None:
            ssl_listener = alb.add_listener("SSLListener", port=443)

            ssl_listener.add_certificates(
                "SSL Listener",
                certificates=[elbv2.ListenerCertificate(ssl_certificate_arn)],
            )

            ssl_listener.add_targets(
                "WebTarget",
                protocol=elbv2.ApplicationProtocol.HTTP,
                targets=[web_service.load_balancer_target(container_name="web")],
            )

            ssl_listener.add_targets(
                "Static",
                port=80,
                targets=[web_service.load_balancer_target(container_name="static")],
                priority=1,
                conditions=[elbv2.ListenerCondition.path_patterns(["/static/*"])],
                health_check=elbv2.HealthCheck(path="/static/drf-yasg/style.css"),
            )

        for service in [web_service, worker_service, schedule_service]:
            service.connections.allow_to(self._tx_database.database_instance, ec2.Port.tcp(5432), "RDS")
            service.connections.allow_to(
                self._tx_redis_cluster_mainnet.connections, ec2.Port.tcp(6379), "Redis"
            )
            service.connections.allow_to(
                self._tx_rabbit_mq.connections, ec2.Port.tcp(5672), "RabbitMQTx"
            )
            service.connections.allow_to(
                events_mq.connections, ec2.Port.tcp(5672), "RabbitMQEvents"
            )
