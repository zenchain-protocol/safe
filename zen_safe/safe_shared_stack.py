import json
import os

from aws_cdk import (
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
    Tags, NestedStack,
)
from constructs import Construct

class SafeSharedStack(NestedStack):

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

        self._secrets = secretsmanager.Secret(
            self,
            "SafeSharedSecrets",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps(
                    {
                        # Mainnet
                        "TX_DJANGO_SECRET_KEY_MAINNET": os.getenv("TX_DJANGO_SECRET_KEY_MAINNET"),
                        "TX_ETHEREUM_NODE_URL_MAINNET": os.getenv("TX_ETHEREUM_NODE_URL_MAINNET"),
                        "TX_ETHEREUM_TRACING_NODE_URL_MAINNET": os.getenv("TX_ETHEREUM_TRACING_NODE_URL_MAINNET"),
                        "TX_ETHERSCAN_API_KEY_MAINNET": os.getenv("TX_ETHERSCAN_API_KEY_MAINNET"),
                        # Configuration Service
                        "CFG_SECRET_KEY": os.getenv("CFG_SECRET_KEY"),
                        "CFG_DJANGO_SUPERUSER_USERNAME": os.getenv("CFG_DJANGO_SUPERUSER_USERNAME"),
                        "CFG_DJANGO_SUPERUSER_PASSWORD": os.getenv("CFG_DJANGO_SUPERUSER_PASSWORD"),
                        "CFG_DJANGO_SUPERUSER_EMAIL": os.getenv("CFG_DJANGO_SUPERUSER_EMAIL"),
                        # Client Gateway
                        "CGW_WEBHOOK_TOKEN": os.getenv("CGW_WEBHOOK_TOKEN"),
                        "CGW_JWT_SECRET": os.getenv("CGW_JWT_SECRET"),
                        "CGW_PRICES_PROVIDER_API_KEY": os.getenv("CGW_PRICES_PROVIDER_API_KEY"),
                        "CGW_REDIS_PASS": os.getenv("CGW_REDIS_PASS"),
                        # Events
                        "EVENTS_ADMIN_EMAIL": os.getenv("EVENTS_ADMIN_EMAIL"),
                        "EVENTS_ADMIN_PASSWORD": os.getenv("EVENTS_ADMIN_PASSWORD"),
                        "EVENTS_SSE_AUTH_TOKEN": os.getenv("EVENTS_SSE_AUTH_TOKEN"),
                    }
                ),
                generate_string_key="password",
                # Needed just so we can provision secrets manager with a template. Not used.
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
