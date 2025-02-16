from typing import Optional
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_rds as rds,
    Stack,
)
from constructs import Construct

from zen_safe.safe_shared_stack import SafeSharedStack
from zen_safe.rabbitmq_construct import RabbitMQConstruct

class SafeEventsStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        shared_stack: SafeSharedStack,
        database: rds.IDatabaseInstance,
        events_mq: RabbitMQConstruct,
        ssl_certificate_arn: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ecs_cluster = ecs.Cluster(
            self,
            "SafeCluster",
            enable_fargate_capacity_providers=True,
            vpc=vpc,
        )

        container_args = {
            "image": ecs.ContainerImage.from_asset("docker/events"),
            "environment": {
                "AMQP_EXCHANGE": "safe-transaction-service-events",
                "AMQP_QUEUE": "safe-events-service",
                "NODE_ENV": "production",
                "URL_BASE_PATH": "/events",
                "WEBHOOKS_CACHE_TTL": "300000",
                "DATABASE_SSL_ENABLED": "false",
            },
            "secrets": {
                "ADMIN_EMAIL": ecs.Secret.from_secrets_manager(
                    shared_stack.secrets, "EVENTS_ADMIN_EMAIL"
                ),
                "ADMIN_PASSWORD": ecs.Secret.from_secrets_manager(
                    shared_stack.secrets, "EVENTS_ADMIN_PASSWORD"
                ),
                "AMQP_URL": ecs.Secret.from_secrets_manager(
                    shared_stack.secrets, "EVENTS_MQ_URL"
                ),
                "DATABASE_URL": ecs.Secret.from_secrets_manager(
                    shared_stack.secrets, "EVENTS_DATABASE_URL"
                ),
                "SSE_AUTH_TOKEN": ecs.Secret.from_secrets_manager(
                    shared_stack.secrets, "EVENTS_SSE_AUTH_TOKEN"
                ),
            },
        }

        ## Web
        web_task_definition = ecs.FargateTaskDefinition(
            self,
            "SafeEventsServiceWeb",
            cpu=512,
            memory_limit_mib=1024,
            family="SafeServices",
        )

        web_task_definition.add_container(
            "Web",
            container_name="web",
            working_directory="/",
            logging=ecs.AwsLogDriver(
                log_group=shared_stack.log_group,
                stream_prefix="Web",
                mode=ecs.AwsLogDriverMode.NON_BLOCKING,
            ),
            port_mappings=[ecs.PortMapping(container_port=3666)],
            **container_args,
        )

        service = ecs.FargateService(
            self,
            "WebService",
            cluster=ecs_cluster,
            task_definition=web_task_definition,
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            enable_execute_command=True,
            desired_count=1,
        )

        ## Setup LB and redirect traffic to web and static containers

        listener = shared_stack.client_gateway_alb.add_listener("Listener", port=80)

        listener.add_targets(
            "WebTarget",
            port=80,
            targets=[service.load_balancer_target(container_name="web")],
            health_check=elbv2.HealthCheck(path="/health"),
        )

        if ssl_certificate_arn is not None:
            ssl_listener = shared_stack.client_gateway_alb.add_listener(
                "SSLListener", port=443
            )

            # Use add_certificates instead of add_certificate_arns
            ssl_listener.add_certificates(
                "SSL Listener",
                certificates=[elbv2.ListenerCertificate(ssl_certificate_arn)], # Use ListenerCertificate
            )


            ssl_listener.add_targets(
                "WebTarget",
                protocol=elbv2.ApplicationProtocol.HTTP,
                targets=[service.load_balancer_target(container_name="web")],
                health_check=elbv2.HealthCheck(path="/health"),
            )

        for svc in [service]:
            service.connections.allow_to(database, ec2.Port.tcp(5432), "RDS")
            svc.connections.allow_to(
                events_mq.connections, ec2.Port.tcp(5672), "RabbitMQEvents"
            )