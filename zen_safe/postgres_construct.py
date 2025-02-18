from aws_cdk import (
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    SecretValue,
    Fn,
)
from constructs import Construct

class PostgresDatabaseConstruct(Construct):
    @property
    def database_instance(self):
        return self._database_instance

    @property
    def connection_string_secret(self):
        return self._connection_string_secret

    @property
    def secret(self):
        return self._database_instance.secret

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        database_name: str = "postgres",
        instance_type: ec2.InstanceType = ec2.InstanceType.of(
            ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.SMALL
        ),
        engine_version: rds.PostgresEngineVersion = rds.PostgresEngineVersion.VER_16_3,
        max_allocated_storage: int = 500,
    ) -> None:
        super().__init__(scope, construct_id)

        database_options = {
            "engine": rds.DatabaseInstanceEngine.postgres(
                version=engine_version
            ),
            "instance_type": instance_type,
            "vpc": vpc,
            "vpc_subnets": ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            "max_allocated_storage": max_allocated_storage,
        }

        # Explicitly create a Secrets Manager secret for database credentials
        self._credentials_secret = secretsmanager.Secret(
            self,
            "DatabaseCredentialsSecret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "postgres"}',
                generate_string_key="password",
                exclude_punctuation=True,
                password_length=16
            )
        )

        self._database_instance = rds.DatabaseInstance(
            self,
            "DatabaseInstance",
            **{**database_options, "credentials": rds.Credentials.from_secret(self._credentials_secret)}
        )

        # Construct the database connection URL
        connection_string = Fn.join(
            '',
            [
                "postgresql://",
                self._credentials_secret.secret_value_from_json("username").unsafe_unwrap(),
                ":",
                self._credentials_secret.secret_value_from_json("password").unsafe_unwrap(),
                "@",
                self._database_instance.db_instance_endpoint_address,
                ":",
                self._database_instance.db_instance_endpoint_port,
                "/",
                database_name
            ]
        )

        # Store the database URL in a *separate* Secrets Manager secret
        self._connection_string_secret = secretsmanager.Secret(
            self, "DatabaseUrlSecret",
            secret_name=f"{construct_id.lower()}-database-url",
            secret_string_value=SecretValue.unsafe_plain_text(connection_string)
        )