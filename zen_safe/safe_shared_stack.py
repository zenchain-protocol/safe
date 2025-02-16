import json

from aws_cdk import (
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_logs as logs,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    Stack,
    Tags,
)
from constructs import Construct

from zen_safe.rabbitmq_construct import RabbitMQConstruct


class SafeSharedStack(Stack):

    @property
    def mainnet_database(self):
        return self._tx_database

    @property
    def events_database(self):
        return self._events_database

    @property
    def tx_mq(self):
        return self._tx_rabbit_mq

    @property
    def events_mq(self):
        return self._events_rabbit_mq

    @property
    def log_group(self):
        return self._log_group

    @property
    def secrets(self):
        return self._secrets

    @property
    def config_alb(self):
        return self._config_alb

    @property
    def transaction_mainnet_alb(self):
        return self._transaction_mainnet_alb

    @property
    def client_gateway_alb(self):
        return self._client_gateway_alb

    @property
    def events_alb(self):
        return self._events_alb

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Tx service
        self._tx_rabbit_mq = RabbitMQConstruct(self, "TxRabbitMQ", vpc=vpc, mq_node_type="mq.t3.small")

        # Events service
        self._events_rabbit_mq = RabbitMQConstruct(self, "EventsRabbitMQ", vpc=vpc, mq_node_type="mq.t3.small")

        self._secrets = secretsmanager.Secret(
            self,
            "SafeSharedSecrets",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps(
                    {
                        # Mainnet
                        "TX_DJANGO_SECRET_KEY_MAINNET": "",
                        "TX_DATABASE_URL_MAINNET": "",
                        "TX_MQ_URL_MAINNET": self._tx_rabbit_mq.authenticated_url,
                        "TX_ETHEREUM_NODE_URL_MAINNET": "",
                        "TX_ETHEREUM_TRACING_NODE_URL_MAINNET": "",
                        "TX_ETHERSCAN_API_KEY_MAINNET": "",
                        # Configuration Service
                        "CFG_SECRET_KEY": "",
                        "CFG_DJANGO_SUPERUSER_USERNAME": "",
                        "CFG_DJANGO_SUPERUSER_PASSWORD": "",
                        "CFG_DJANGO_SUPERUSER_EMAIL": "",
                        # Client Gateway
                        "CGW_WEBHOOK_TOKEN": "",
                        "CGW_JWT_SECRET": "",
                        "CGW_PRICES_PROVIDER_API_KEY": "",
                        # Events
                        "EVENTS_DATABASE_URL": "",
                        "EVENTS_MQ_URL": self._events_rabbit_mq.authenticated_url,
                        "EVENTS_ADMIN_EMAIL": "",
                        "EVENTS_ADMIN_PASSWORD": "",
                        "EVENTS_SSE_AUTH_TOKEN": "",
                    }
                ),
                generate_string_key="password",  # Needed just so we can provision secrets manager with a template. Not used.
            ),
        )

        self._config_alb = elbv2.ApplicationLoadBalancer(
            self, "CfgSafe", vpc=vpc, internet_facing=True
        )
        Tags.of(self._config_alb).add("Name", "Safe Config")

        self._transaction_mainnet_alb = elbv2.ApplicationLoadBalancer(
            self, "TxSafeMainnet", vpc=vpc, internet_facing=True
        )
        Tags.of(self._transaction_mainnet_alb).add(
            "Name", "Safe Transaction Mainnet"
        )

        self._client_gateway_alb = elbv2.ApplicationLoadBalancer(
            self, "ClientGatewaySafe", vpc=vpc, internet_facing=True
        )
        Tags.of(self._client_gateway_alb).add("Name", "Safe Client Gateway")


        self._events_alb = elbv2.ApplicationLoadBalancer(
            self, "EventsSafe", vpc=vpc, internet_facing=True
        )
        Tags.of(self._events_alb).add("Name", "Safe Events")

        self._log_group = logs.LogGroup(
            self, "LogGroup", retention=logs.RetentionDays.ONE_MONTH
        )

        # The databases for the transaction and events services need to be defined here because we need the
        # database credentials as database URLs.
        # This can't be done dynamically because of limitations of CDK/Cloud Formation.

        database_options = {
            "engine": rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16_3
            ),
            "instance_type": ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.SMALL
            ),
            "vpc": vpc,
            "vpc_subnets": ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            "max_allocated_storage": 500,
            "credentials": rds.Credentials.from_generated_secret("postgres"),
        }

        self._tx_database = rds.DatabaseInstance(
            self,
            "MainnetTxDatabase",
            **database_options,
        )

        self._events_database = rds.DatabaseInstance(
            self,
            "EventsDatabase",
            **database_options,
        )
