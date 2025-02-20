from typing import Optional, Union
from aws_cdk import (
    aws_ec2 as ec2,
    Stack
)
from constructs import Construct

from zen_safe.safe_client_gateway_stack import \
    SafeClientGatewayStack
from zen_safe.safe_configuration_stack import \
    SafeConfigurationStack
from zen_safe.safe_events_stack import SafeEventsStack
from zen_safe.safe_shared_stack import SafeSharedStack
from zen_safe.safe_transaction_stack import \
    SafeTransactionStack
from zen_safe.safe_ui_stack import SafeUIStack


class ZenSafeStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment_name: str,
        ui_subdomain: Union[str, None],
        config_service_uri: Optional[str] = None,
        client_gateway_url: Optional[str] = None,
        mainnet_transaction_gateway_url: Optional[str] = None,
        ssl_certificate_arn: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(self, "SafeVPC", max_azs=2)

        shared_stack = SafeSharedStack(self, "SafeShared", vpc=vpc)

        events_stack = SafeEventsStack(
            self,
            "SafeEvents",
            vpc=vpc,
            shared_stack=shared_stack,
            ssl_certificate_arn=ssl_certificate_arn,
        )

        transaction_mainnet_stack = SafeTransactionStack(
            self,
            "SafeTxMainnet",
            vpc=vpc,
            shared_stack=shared_stack,
            chain_name="mainnet",
            events_mq=events_stack.events_mq,
            alb=shared_stack.transaction_mainnet_alb,
            number_of_workers=4,
            ssl_certificate_arn=ssl_certificate_arn,
        )

        client_gateway_stack = SafeClientGatewayStack(
            self,
            "SafeCGW",
            vpc=vpc,
            shared_stack=shared_stack,
            ssl_certificate_arn=ssl_certificate_arn,
            client_gateway_url=client_gateway_url,
            config_service_uri=config_service_uri,
        )

        configuration_stack = SafeConfigurationStack(
            self,
            "SafeCfg",
            vpc=vpc,
            shared_stack=shared_stack,
            ssl_certificate_arn=ssl_certificate_arn,
            client_gateway_url=client_gateway_url,
            config_service_uri=config_service_uri,
            mainnet_transaction_gateway_url=mainnet_transaction_gateway_url,
        )

        # Dependencies (CDK v2 often infers these, but keep for compatibility)
        configuration_stack.node.add_dependency(client_gateway_stack)
        configuration_stack.node.add_dependency(shared_stack)
        transaction_mainnet_stack.node.add_dependency(shared_stack)
        client_gateway_stack.node.add_dependency(shared_stack)
        events_stack.node.add_dependency(shared_stack)

        SafeUIStack(
            self,
            "SafeUI",
            environment_name=environment_name,
            shared_stack=shared_stack,
            subdomain_name=ui_subdomain,
            allowed_origins=[
                "https://safe.zenchain.io",
                "https://txs.safe.zenchain.io"
            ],
        )