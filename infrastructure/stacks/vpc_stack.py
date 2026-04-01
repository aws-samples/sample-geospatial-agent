from aws_cdk import (
    Stack,
    CfnOutput,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct
from cdk_nag import NagSuppressions


class VPCStack(Stack):
    """Stack for VPC with NAT Gateway"""

    def __init__(self, scope: Construct, construct_id: str,  **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self, "AgentVpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(cidr_mask=24, name="Public", subnet_type=ec2.SubnetType.PUBLIC),
                ec2.SubnetConfiguration(cidr_mask=24, name="Private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            ],
        )



        # VPC Flow Logs
        flow_log_role = iam.Role(self, "FlowLogRole", assumed_by=iam.ServicePrincipal("vpc-flow-logs.amazonaws.com"))
        flow_log_group = logs.LogGroup(self, "VpcFlowLogGroup", retention=logs.RetentionDays.ONE_WEEK)
        flow_log_group.grant_write(flow_log_role)
        ec2.FlowLog(self, "VpcFlowLog", resource_type=ec2.FlowLogResourceType.from_vpc(self.vpc),
                    destination=ec2.FlowLogDestination.to_cloud_watch_logs(flow_log_group, flow_log_role))

        CfnOutput(self, "VpcId", value=self.vpc.vpc_id)
        CfnOutput(self, "PrivateSubnetIds", value=",".join([s.subnet_id for s in self.vpc.private_subnets]))

        NagSuppressions.add_resource_suppressions(flow_log_role,
            [{"id": "AwsSolutions-IAM4", "reason": "Flow log role uses service-linked permissions"}])
