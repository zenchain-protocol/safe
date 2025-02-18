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
from zen_safe.redis_construct import RedisConstruct

class SafeClientGatewayStack(Stack):
    @property
    def redis_cluster(self):
        return self._redis_cluster

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        shared_stack: SafeSharedStack,
        cache_node_type: str = "cache.t3.small",
        ssl_certificate_arn: Optional[str] = None,
        config_service_uri: Optional[str] = None,
        client_gateway_url: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        if client_gateway_url is None:
            client_gateway_url = shared_stack.client_gateway_alb.load_balancer_dns_name

        if config_service_uri is None:
            config_service_uri = f"http://{shared_stack.config_alb.load_balancer_dns_name}"

        self._redis_cluster = RedisConstruct(
            self,
            "RedisCluster",
            vpc=vpc,
            auth_token=shared_stack.secrets.secret_value_from_json("CGW_REDIS_PASS").to_string(),
            cache_node_type=cache_node_type
        )

        database = rds.DatabaseInstance(
            self,
            "CgwDatabase",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16_3
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.SMALL
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            max_allocated_storage=500,
            credentials=rds.Credentials.from_generated_secret("postgres"),
        )

        ecs_cluster = ecs.Cluster(
            self,
            "SafeCluster",
            enable_fargate_capacity_providers=True,
            vpc=vpc,
        )

        container_args = {
            "image": ecs.ContainerImage.from_asset("docker/client-gateway"),
            "environment": {
                "JWT_ISSUER": client_gateway_url,
                "SAFE_CONFIG_BASE_URI": config_service_uri,
                "SAFE_WEB_APP_BASE_URI": "https://safe.zenchain.io",
                "LOG_LEVEL": "info",
                "POSTGRES_DB": "postgres",
                "REDIS_HOST": self.redis_cluster.cluster.attr_primary_end_point_address,
                "REDIS_PORT": self.redis_cluster.cluster.attr_primary_end_point_port,
                "HTTP_CLIENT_REQUEST_TIMEOUT_MILLISECONDS": "60000",
            },
            "secrets": {
                "JWT_SECRET": ecs.Secret.from_secrets_manager(
                    shared_stack.secrets, "CGW_JWT_SECRET"
                ),
                "AUTH_TOKEN": ecs.Secret.from_secrets_manager(
                    shared_stack.secrets, "CGW_WEBHOOK_TOKEN"
                ),
                "REDIS_PASS": ecs.Secret.from_secrets_manager(
                    shared_stack.secrets, "CGW_REDIS_PASS"
                ),
                "PRICES_PROVIDER_API_KEY": ecs.Secret.from_secrets_manager(
                    shared_stack.secrets, "CGW_PRICES_PROVIDER_API_KEY"
                ),
                "POSTGRES_USER": ecs.Secret.from_secrets_manager(
                    database.secret, "username"
                ),
                "POSTGRES_PASSWORD": ecs.Secret.from_secrets_manager(
                    database.secret, "password"
                ),
                "POSTGRES_HOST": ecs.Secret.from_secrets_manager(
                    database.secret, "host"
                ),
                "POSTGRES_PORT": ecs.Secret.from_secrets_manager(
                    database.secret, "port"
                ),
            },
        }

        ## Web
        web_task_definition = ecs.FargateTaskDefinition(
            self,
            "SafeCGWServiceWeb",
            cpu=512,
            memory_limit_mib=1024,
            family="SafeServices",
        )

        web_task_definition.add_container(
            "Web",
            container_name="web",
            working_directory="/app",
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
                self.redis_cluster.connections, ec2.Port.tcp(6379), "Redis"
            )