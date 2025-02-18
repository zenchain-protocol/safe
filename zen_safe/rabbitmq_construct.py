from aws_cdk import (
    aws_ec2 as ec2,
    Tags,
    aws_secretsmanager as secretsmanager,
    aws_amazonmq as mq,
    CfnOutput, Fn,
)
from constructs import Construct
from urllib.parse import urlparse


class RabbitMQConstruct(Construct):
    @property
    def authenticated_url(self):
        return self._authenticated_url

    @property
    def amqp_url(self):
        return self._amqp_url

    @property
    def amqp_host(self):
        return self._amqp_host

    @property
    def amqp_port(self):
        return self._amqp_port

    @property
    def connections(self):
        return self._connections

    @property
    def secret(self):  # Expose the secret
        return self._secret

    @property
    def broker(self): # Expose the broker
        return self._broker

    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.IVpc, mq_node_type: str="mq.t3.small") -> None:
        super().__init__(scope, construct_id)

        sg_rabbitmq = ec2.SecurityGroup(
            self,
            "RabbitMQServerSG",
            vpc=vpc,
            allow_all_outbound=True,
            description="Security group for RabbitMQ",
        )
        Tags.of(sg_rabbitmq).add("Name", "rabbitmq-server")

        sg_rabbitmq.add_ingress_rule(
            peer=sg_rabbitmq,
            connection=ec2.Port.all_tcp(),
            description="Allow all traffic within the SG",
        )

        self._connections = ec2.Connections(
            security_groups=[sg_rabbitmq], default_port=ec2.Port.tcp(5671)
        )

        # Create a Secrets Manager secret for the RabbitMQ user and password
        self._secret = secretsmanager.Secret(
            self, f"RabbitMQSecret",
            secret_name=f"rabbitmq-credentials",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "rabbitmq", "url": ""}',
                generate_string_key="password",
                exclude_punctuation=True,
            )
        )

        # Create the RabbitMQ broker
        self._broker = mq.CfnBroker(
            self, "RabbitMQBroker",
            broker_name="MyRabbitMQBroker",
            engine_type="RabbitMQ",
            engine_version="3.13.x",
            host_instance_type=mq_node_type,
            publicly_accessible=False,
            subnet_ids=vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS).subnet_ids,
            security_groups=[sg_rabbitmq.security_group_id],
            users=[
                mq.CfnBroker.UserProperty(
                    username=self._secret.secret_value_from_json("username").to_string(),
                    password=self._secret.secret_value_from_json("password").to_string(),
                )
            ],
            auto_minor_version_upgrade=True,
            deployment_mode="SINGLE_INSTANCE"
        )

        self._amqp_url = Fn.select(0, self._broker.attr_amqp_endpoints)
        self._authenticated_url = create_mq_connection_string(
            username=self._secret.secret_value_from_json("username").to_string(),
            password=self._secret.secret_value_from_json("password").to_string(),
            host=urlparse(self._amqp_url).hostname,
            port=5671
        )
        self._amqp_host = urlparse(self._amqp_url).hostname
        self._amqp_port = 5671

         # Output the AMQP URL and other useful attributes
        CfnOutput(self, "RabbitMQAmqpUrl", value=self._amqp_url)
        CfnOutput(self, "RabbitMQArn", value=self.broker.attr_arn)

def create_mq_connection_string(username: str, password: str, host: str, port: int) -> str:
    return f"amqp+ssl://{username}:{password}@{host}:{port}/"
