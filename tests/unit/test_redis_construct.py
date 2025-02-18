from aws_cdk import (
    assertions,
    App,
    aws_ec2 as ec2,
)
import aws_cdk as cdk
from zen_safe.redis_construct import RedisConstruct


def test_redis_construct_creation():
    """Test if RedisConstruct creates all required resources."""
    app = App()
    env = cdk.Environment(account="123456789012", region="us-east-1")
    test_stack = cdk.Stack(app, "TestStack", env=env)
    vpc = ec2.Vpc(test_stack, "TestVPC")
    redis_construct = RedisConstruct(test_stack, "TestRedisConstruct", vpc, "cache.t3.small")
    template = assertions.Template.from_stack(test_stack)

    # Verify Redis replication group resource exists
    template.resource_count_is("AWS::ElastiCache::ReplicationGroup", 1)

    # Verify properties of the replication group
    template.has_resource_properties("AWS::ElastiCache::ReplicationGroup", {
        "Engine": "redis",
        "EngineVersion": "7.x",
        "AutomaticFailoverEnabled": True,
        "MultiAZEnabled": True,
        "NumNodeGroups": 1,
        "ReplicasPerNodeGroup": 1,
    })


def test_redis_construct_security_group():
    """Test if RedisConstruct creates a security group with the correct properties."""
    app = App()
    env = cdk.Environment(account="123456789012", region="us-east-1")
    test_stack = cdk.Stack(app, "TestStack", env=env)
    vpc = ec2.Vpc(test_stack, "TestVPC")
    redis_construct = RedisConstruct(test_stack, "TestRedisConstruct", vpc, "cache.t3.small")
    template = assertions.Template.from_stack(test_stack)

    # Verify the security group resource exists
    template.resource_count_is("AWS::EC2::SecurityGroup", 1)

    # Verify security group ingress rule
    template.has_resource_properties("AWS::EC2::SecurityGroupIngress", {
        "Description": "default-redis-server",
        "IpProtocol": "tcp",
    })


def test_redis_construct_parameter_group():
    """Test if RedisConstruct creates a parameter group with correct properties."""
    app = App()
    env = cdk.Environment(account="123456789012", region="us-east-1")
    test_stack = cdk.Stack(app, "TestStack", env=env)
    vpc = ec2.Vpc(test_stack, "TestVPC")
    redis_construct = RedisConstruct(test_stack, "TestRedisConstruct", vpc, "cache.t3.small")
    template = assertions.Template.from_stack(test_stack)

    # Verify the parameter group resource exists
    template.resource_count_is("AWS::ElastiCache::ParameterGroup", 1)

    # Verify properties of the parameter group
    template.has_resource_properties("AWS::ElastiCache::ParameterGroup", {
        "CacheParameterGroupFamily": "redis7.x",
        "Description": "parameter group for redis7.x",
        "Properties": {
            "databases": "256",
        }
    })


def test_redis_construct_subnet_group():
    """Test if RedisConstruct creates a subnet group with proper configuration."""
    app = App()
    env = cdk.Environment(account="123456789012", region="us-east-1")
    test_stack = cdk.Stack(app, "TestStack", env=env)
    vpc = ec2.Vpc(test_stack, "TestVPC")
    redis_construct = RedisConstruct(test_stack, "TestRedisConstruct", vpc, "cache.t3.small")
    template = assertions.Template.from_stack(test_stack)

    # Verify the subnet group resource exists
    template.resource_count_is("AWS::ElastiCache::SubnetGroup", 1)

    # Verify properties of the subnet group
    template.has_resource_properties("AWS::ElastiCache::SubnetGroup", {
        "Description": "subnet group for redis",
    })
