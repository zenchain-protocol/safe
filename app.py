#!/usr/bin/env python3
import os

from aws_cdk import App, Environment, Tags

from zen_safe.safe_stack import ZenSafeStack

app = App()
environment = Environment(
    account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
    region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
)

ui_subdomain = os.environ.get("UI_SUBDOMAIN")

config_service_uri = os.environ.get("CONFIG_SERVICE_URI")
client_gateway_url = os.environ.get("CLIENT_GATEWAY_URL")
mainnet_transaction_gateway_url = os.environ.get("MAINNET_TRANSACTION_GATEWAY_URL")

ssl_certificate_arn = os.environ.get("SSL_CERTIFICATE_ARN")

environment_name = "production"
prod_stack = ZenSafeStack(
    app,
    "SafeStack",
    ui_subdomain=ui_subdomain,
    environment_name=environment_name,
    config_service_uri=config_service_uri,
    client_gateway_url=client_gateway_url,
    mainnet_transaction_gateway_url=mainnet_transaction_gateway_url,
    ssl_certificate_arn=ssl_certificate_arn,
    env=environment,
)

Tags.of(prod_stack).add("environment", environment_name)
Tags.of(prod_stack).add("app", "Safe")

app.synth()