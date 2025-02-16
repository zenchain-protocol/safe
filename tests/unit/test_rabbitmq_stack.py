from aws_cdk import (
    assertions,
    App,
    aws_ec2 as ec2
)
from zen_safe.rabbitmq_construct import RabbitMQConstruct


def test_rabbitmq_stack_creation():
    """Test if RabbitMQ stack creates all required resources."""
    app = App()
    vpc = ec2.Vpc(app, "TestVPC")
    stack = RabbitMQConstruct(app, "TestRabbitMQStack", vpc, "mq.t3.micro")
    template = assertions.Template.from_stack(stack)

    # Verify RabbitMQ broker resource exists
    template.resource_count_is("AWS::AmazonMQ::Broker", 1)

    # Verify broker configuration
    template.has_resource_properties("AWS::AmazonMQ::Broker", {
        "EngineType": "RabbitMQ",
        "HostInstanceType": "mq.t3.micro",
        "PubliclyAccessible": False
    })


def test_rabbitmq_stack_outputs():
    """Test if RabbitMQ stack creates all required outputs with correct properties."""
    app = App()
    vpc = ec2.Vpc(app, "TestVPC")
    stack = RabbitMQConstruct(app, "TestRabbitMQStack", vpc)
    template = assertions.Template.from_stack(stack)

    # Verify required outputs exist with correct properties
    template.has_output("RabbitMQAmqpUrl", {
        "Description": assertions.Match.any_value
    })
    template.has_output("RabbitMQArn", {
        "Description": assertions.Match.any_value()
    })


def test_rabbitmq_vpc_configuration():
    """Test if RabbitMQ broker is properly configured with VPC settings."""
    app = App()
    vpc = ec2.Vpc(app, "TestVPC")
    stack = RabbitMQConstruct(app, "TestRabbitMQStack", vpc)
    template = assertions.Template.from_stack(stack)

    # Verify VPC configuration
    template.has_resource_properties("AWS::AmazonMQ::Broker", {
        "SubnetIds": assertions.Match.any_value,
        "SecurityGroups": assertions.Match.any_value
    })
