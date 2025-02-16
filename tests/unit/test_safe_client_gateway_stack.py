import aws_cdk as cdk
from aws_cdk.assertions import Template
from zen_safe.safe_client_gateway_stack import SafeClientGatewayStack
from zen_safe.safe_shared_stack import SafeSharedStack
from aws_cdk import aws_ec2 as ec2


class TestSafeClientGatewayStack:
    app = cdk.App()
    env = cdk.Environment(account="123456789012", region="us-east-1")
    vpc = ec2.Vpc(app, "TestVpc", cidr="10.0.0.0/16")
    shared_stack = SafeSharedStack(
        app,
        "TestSharedStack",
        vpc=vpc,
        env=env
    )

    def test_client_gateway_alb_created(self):
        stack = SafeClientGatewayStack(
            self.app,
            "TestClientGatewayStack",
            vpc=self.vpc,
            shared_stack=self.shared_stack,
            env=self.env
        )
        template = Template.from_stack(stack)

        template.resource_count_is("AWS::ElasticLoadBalancingV2::LoadBalancer", 1)
        template.has_resource_properties(
            "AWS::ElasticLoadBalancingV2::LoadBalancer",
            {
                "Scheme": "internet-facing",
                "Type": "application",
                "VpcId": {
                    "Ref": "TestVpc"
                },
                "Name": "ClientGatewaySafe"
            }
        )

    def test_ecs_fargate_service_web_created(self):
        stack = SafeClientGatewayStack(
            self.app,
            "TestClientGatewayStack",
            vpc=self.vpc,
            shared_stack=self.shared_stack,
            env=self.env
        )
        template = Template.from_stack(stack)

        template.resource_count_is("AWS::ECS::Service", 1)
        template.has_resource_properties(
            "AWS::ECS::Service",
            {
                "LaunchType": "FARGATE",
                "DesiredCount": 1,
                "DeploymentConfiguration": {
                    "DeploymentCircuitBreaker": {
                        "Enable": True,
                        "Rollback": True
                    }
                },
                "EnableExecuteCommand": True,
                "Cluster": {
                    "Fn::GetAtt": [
                        "TestClientGatewayStackSafeClusterCCE7E932",
                        "Arn"
                    ]
                },
                "TaskDefinition": {
                    "Ref": "TestClientGatewayStackSafeClientGatewayServiceWebTaskDefC753C6D4"
                }
            }
        )

    def test_ecs_task_definition_web_container_configured(self):
        stack = SafeClientGatewayStack(
            self.app,
            "TestClientGatewayStack",
            vpc=self.vpc,
            shared_stack=self.shared_stack,
            env=self.env
        )
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::ECS::TaskDefinition",
            {
                "Family": "SafeServices",
                "Cpu": "512",
                "Memory": "1024",
                "NetworkMode": "awsvpc",
                "RequiresCompatibilities": [
                    "FARGATE",
                    "EC2"
                ],
                "ExecutionRoleArn": {
                    "Fn::GetAtt": [
                        "TestClientGatewayStackSafeClientGatewayServiceWebTaskDefExecutionRole6987968F",
                        "Arn"
                    ]
                },
                "TaskRoleArn": {
                    "Fn::GetAtt": [
                        "TestClientGatewayStackSafeClientGatewayServiceWebTaskDefTaskRole811176A2",
                        "Arn"
                    ]
                },
                "ContainerDefinitions": [
                    {
                        "Name": "Web",
                        "Image": {
                            "Fn::Join": [
                                "",
                                [
                                    {
                                        "Fn::Sub": "arn:${AWS::Partition}:ecr:${AWS::Region}:123456789012:repository"
                                    },
                                    "/safe-client-gateway"
                                ]
                            ]
                        },
                        "PortMappings": [
                            {
                                "ContainerPort": 8002
                            }
                        ],
                        "Environment": [
                            {
                                "Name": "PYTHONDONTWRITEBYTECODE",
                                "Value": "true"
                            },
                            {
                                "Name": "DEBUG",
                                "Value": "true"
                            },
                            {
                                "Name": "ROOT_LOG_LEVEL",
                                "Value": "DEBUG"
                            },
                            {
                                "Name": "DJANGO_ALLOWED_HOSTS",
                                "Value": "*"
                            },
                            {
                                "Name": "GUNICORN_BIND_PORT",
                                "Value": "8002"
                            },
                            {
                                "Name": "DOCKER_NGINX_VOLUME_ROOT",
                                "Value": "/nginx"
                            },
                            {
                                "Name": "GUNICORN_BIND_SOCKET",
                                "Value": "unix:/gunicorn.socket"
                            },
                            {
                                "Name": "NGINX_ENVSUBST_OUTPUT_DIR",
                                "Value": "/etc/nginx/"
                            },
                            {
                                "Name": "CGW_PRICES_PROVIDER_URL",
                                "Value": "http://localhost:8004"
                            },
                            {
                                "Name": "CGW_INFURA_PROJECT_ID",
                                "Value": ""
                            },
                            {
                                "Name": "CGW_ALCHEMY_API_KEY",
                                "Value": ""
                            },
                            {
                                "Name": "CGW_POCKET_NETWORK_APPLICATION_ID",
                                "Value": ""
                            },
                            {
                                "Name": "CGW_POCKET_NETWORK_SECRET_KEY",
                                "Value": ""
                            },
                            {
                                "Name": "CGW_COINGECKO_API_KEY",
                                "Value": ""
                            },
                            {
                                "Name": "CGW_CURRENCY_CONVERTER_URL",
                                "Value": "https://api.exchangerate.host"
                            },
                             {
                                "Name": "FORCE_SCRIPT_NAME",
                                "Value": "/cgw/"
                            },
                            {
                                "Name": "CSRF_TRUSTED_ORIGINS",
                                "Value": "https://safe.zenchain.io"
                            }
                        ],
                        "Secrets": [
                            {
                                "Name": "WEBHOOK_TOKEN",
                                "ValueFrom": {
                                    "Fn::Sub": "arn:${AWS::Partition}:secretsmanager:us-east-1:123456789012:secret:SafeSharedSecrets-xxxxx:CGW_WEBHOOK_TOKEN::"
                                }
                            },
                            {
                                "Name": "JWT_SECRET",
                                "ValueFrom": {
                                    "Fn::Sub": "arn:${AWS::Partition}:secretsmanager:us-east-1:123456789012:secret:SafeSharedSecrets-xxxxx:CGW_JWT_SECRET::"
                                }
                            },
                             {
                                "Name": "PRICES_PROVIDER_API_KEY",
                                "ValueFrom": {
                                    "Fn::Sub": "arn:${AWS::Partition}:secretsmanager:us-east-1:123456789012:secret:SafeSharedSecrets-xxxxx:CGW_PRICES_PROVIDER_API_KEY::"
                                }
                            }
                        ],
                        "LogConfiguration": {
                            "LogDriver": "awslogs",
                            "Options": {
                                "awslogs-group": {
                                    "Ref": "TestSharedStackTestSharedStackLogGroupF4C0194F"
                                },
                                "awslogs-stream-prefix": "Web",
                                "awslogs-non-blocking": "true"
                            }
                        },
                        "MountPoints": [
                            {
                                "SourceVolume": "nginx_volume",
                                "ContainerPath": "/app/staticfiles",
                                "ReadOnly": False
                            }
                        ]
                    },
                    {
                        "Name": "StaticFiles",
                        "Image": "nginx:latest",
                        "PortMappings": [
                            {
                                "ContainerPort": 80
                            }
                        ],
                        "MountPoints": [
                            {
                                "SourceVolume": "nginx_volume",
                                "ContainerPath": "/usr/share/nginx/html/static",
                                "ReadOnly": True
                            }
                        ]
                    }
                ],
                "Volumes": [
                    {
                        "Name": "nginx_volume"
                    }
                ]
            }
        )

    def test_alb_listener_http_created(self):
        stack = SafeClientGatewayStack(
            self.app,
            "TestClientGatewayStack",
            vpc=self.vpc,
            shared_stack=self.shared_stack,
            env=self.env
        )
        template = Template.from_stack(stack)

        template.resource_count_is("AWS::ElasticLoadBalancingV2::Listener", 1)
        template.has_resource_properties(
            "AWS::ElasticLoadBalancingV2::Listener",
            {
                "DefaultActions": [
                    {
                        "TargetGroupArn": {
                            "Ref": "TestClientGatewayStackClientGatewaySafeListenerWebTargetGroup1964C634"
                        },
                        "Type": "forward"
                    }
                ],
                "LoadBalancerArn": {
                    "Ref": "TestClientGatewayStackClientGatewaySafeB62CF48B"
                },
                "Port": 80,
                "Protocol": "HTTP"
            }
        )

    def test_alb_target_group_web_created(self):
        stack = SafeClientGatewayStack(
            self.app,
            "TestClientGatewayStack",
            vpc=self.vpc,
            shared_stack=self.shared_stack,
            env=self.env
        )
        template = Template.from_stack(stack)

        template.resource_count_is("AWS::ElasticLoadBalancingV2::TargetGroup", 1)
        template.has_resource_properties(
            "AWS::ElasticLoadBalancingV2::TargetGroup",
            {
                "HealthCheckEnabled": True,
                "HealthCheckIntervalSeconds": 30,
                "HealthCheckPath": "/cgw/drf-yasg/style.css",
                "HealthCheckPort": "traffic-port",
                "HealthCheckProtocol": "HTTP",
                "HealthCheckTimeoutSeconds": 10,
                "HealthyThresholdCount": 5,
                "Matcher": {
                    "HttpCode": "200"
                },
                "Name": "WebTargetGroup",
                "Port": 80,
                "Protocol": "HTTP",
                "TargetGroupAttributes": [
                    {
                        "Key": "deregistration_delay.timeout_seconds",
                        "Value": "300"
                    }
                ],
                "TargetType": "ip",
                "VpcId": {
                    "Ref": "TestClientGatewayStackTestVpc8654414FRef"
                }
            }
        )

    def test_alb_listener_http_targets_configured(self):
        stack = SafeClientGatewayStack(
            self.app,
            "TestClientGatewayStack",
            vpc=self.vpc,
            shared_stack=self.shared_stack,
            env=self.env
        )
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::ElasticLoadBalancingV2::ListenerRule",
            {
                "Actions": [
                    {
                        "TargetGroupArn": {
                            "Ref": "TestClientGatewayStackClientGatewaySafeListenerStaticTargetGroup19309471"
                        },
                        "Type": "forward"
                    }
                ],
                "Conditions": [
                    {
                        "Field": "path-pattern",
                        "Values": [
                            "/static/*"
                        ]
                    }
                ],
                "ListenerArn": {
                    "Ref": "TestClientGatewayStackClientGatewaySafeListenerListener87397987"
                },
                "Priority": 1
            }
        )

    def test_alb_target_group_static_created(self):
        stack = SafeClientGatewayStack(
            self.app,
            "TestClientGatewayStack",
            vpc=self.vpc,
            shared_stack=self.shared_stack,
            env=self.env
        )
        template = Template.from_stack(stack)

        template.resource_count_is("AWS::ElasticLoadBalancingV2::TargetGroup", 2) # Expecting 2 target groups, Web and Static
        template.has_resource_properties(
            "AWS::ElasticLoadBalancingV2::TargetGroup",
            {
                "HealthCheckEnabled": True,
                "HealthCheckIntervalSeconds": 30,
                "HealthCheckPath": "/static/drf-yasg/style.css",
                "HealthCheckPort": "traffic-port",
                "HealthCheckProtocol": "HTTP",
                "HealthCheckTimeoutSeconds": 10,
                "HealthyThresholdCount": 5,
                "Matcher": {
                    "HttpCode": "200"
                },
                "Name": "StaticTargetGroup",
                "Port": 80,
                "Protocol": "HTTP",
                "TargetGroupAttributes": [
                    {
                        "Key": "deregistration_delay.timeout_seconds",
                        "Value": "300"
                    }
                ],
                "TargetType": "ip",
                "VpcId": {
                    "Ref": "TestClientGatewayStackTestVpc8654414FRef"
                }
            }
        )

    def test_security_group_configured(self):
        stack = SafeClientGatewayStack(
            self.app,
            "TestClientGatewayStack",
            vpc=self.vpc,
            shared_stack=self.shared_stack,
            env=self.env
        )
        template = Template.from_stack(stack)

        template.resource_count_is("AWS::EC2::SecurityGroup", 2) # Expecting 2 security groups, one for service, one for ALB
        template.has_resource_properties(
            "AWS::EC2::SecurityGroup",
            {
                "GroupDescription": "SecurityGroup for Client Gateway Service",
                "GroupName": "client-gateway-service-security-group",
                "SecurityGroupEgress": [
                    {
                        "CidrIp": "0.0.0.0/0",
                        "Description": "Allow all outbound traffic by default",
                        "IpProtocol": "-1"
                    }
                ],
                "VpcId": {
                    "Ref": "TestClientGatewayStackTestVpc8654414FRef"
                }
            }
        )
