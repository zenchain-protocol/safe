from aws_cdk import (
    assertions,
    App,
    aws_ec2 as ec2
)
import aws_cdk as cdk
from zen_safe.rabbitmq_construct import RabbitMQConstruct


def test_rabbitmq_construct_creation():
    """Test if RabbitMQ stack creates all required resources."""
    app = App()
    env = cdk.Environment(account="123456789012", region="us-east-1")
    test_stack = cdk.Stack(app, "TestStack", env=env)
    vpc = ec2.Vpc(test_stack, "TestVPC")
    mq_construct = RabbitMQConstruct(test_stack, "TestRabbitMQStack", vpc, "mq.t3.micro")
    template = assertions.Template.from_stack(test_stack)

    # Verify RabbitMQ broker resource exists
    template.resource_count_is("AWS::AmazonMQ::Broker", 1)

    # Verify broker configuration
    template.has_resource_properties("AWS::AmazonMQ::Broker", {
        "EngineType": "RabbitMQ",
        "HostInstanceType": "mq.t3.micro",
        "PubliclyAccessible": False
    })


def test_rabbitmq_construct_outputs():
    """Test if RabbitMQ stack creates all required outputs with correct properties."""
    app = App()
    env = cdk.Environment(account="123456789012", region="us-east-1")
    test_stack = cdk.Stack(app, "TestStack", env=env)
    vpc = ec2.Vpc(test_stack, "TestVPC")
    mq_construct = RabbitMQConstruct(test_stack, "TestRabbitMQStack", vpc)
    template = assertions.Template.from_stack(test_stack)

    # Verify required outputs exist with correct properties
    template.has_output("RabbitMQAmqpUrl", {
        "Description": assertions.Match.any_value()
    })
    template.has_output("RabbitMQArn", {
        "Description": assertions.Match.any_value()
    })


def test_rabbitmq_vpc_configuration():
    """Test if RabbitMQ broker is properly configured with VPC settings."""
    app = App()
    env = cdk.Environment(account="123456789012", region="us-east-1")
    test_stack = cdk.Stack(app, "TestStack", env=env)
    vpc = ec2.Vpc(test_stack, "TestVPC")
    mq_construct = RabbitMQConstruct(test_stack, "TestRabbitMQStack", vpc)
    template = assertions.Template.from_stack(test_stack)

    # Verify VPC configuration
    template.has_resource_properties("AWS::AmazonMQ::Broker", {
        "SubnetIds": assertions.Match.any_value(),
        "SecurityGroups": assertions.Match.any_value()
    })
