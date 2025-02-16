from aws_cdk import (
    assertions,
    App,
    aws_ec2 as ec2,
)
from zen_safe.redis_construct import RedisConstruct


def test_redis_construct_creation():
    """Test if RedisConstruct creates all required resources."""
    app = App()
    vpc = ec2.Vpc(app, "TestVPC")
    redis_construct = RedisConstruct(app, "TestRedisConstruct", vpc, "cache.t3.small")
    template = assertions.Template.from_stack(redis_construct)

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
    vpc = ec2.Vpc(app, "TestVPC")
    redis_construct = RedisConstruct(app, "TestRedisConstruct", vpc, "cache.t3.small")
    template = assertions.Template.from_stack(redis_construct)

    # Verify the security group resource exists
    template.resource_count_is("AWS::EC2::SecurityGroup", 1)

    # Verify security group ingress rule
    template.has_resource_properties("AWS::EC2::SecurityGroupIngress", {
        "Description": "default-redis-server",
        "IpProtocol": "-1",
    })


def test_redis_construct_parameter_group():
    """Test if RedisConstruct creates a parameter group with correct properties."""
    app = App()
    vpc = ec2.Vpc(app, "TestVPC")
    redis_construct = RedisConstruct(app, "TestRedisConstruct", vpc, "cache.t3.small")
    template = assertions.Template.from_stack(redis_construct)

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
    vpc = ec2.Vpc(app, "TestVPC")
    redis_construct = RedisConstruct(app, "TestRedisConstruct", vpc, "cache.t3.small")
    template = assertions.Template.from_stack(redis_construct)

    # Verify the subnet group resource exists
    template.resource_count_is("AWS::ElastiCache::SubnetGroup", 1)

    # Verify properties of the subnet group
    template.has_resource_properties("AWS::ElastiCache::SubnetGroup", {
        "Description": "subnet group for redis",
    })
