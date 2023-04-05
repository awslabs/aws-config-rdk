from aws_cdk import (
    # Duration,
    Stack,
    aws_config as config
    # aws_sqs as sqs,
)
from constructs import Construct
from pathlib import Path

class CdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # example resource
        # queue = sqs.Queue(
        #     self, "RdkCdkQueue",
        #     visibility_timeout=Duration.seconds(300),
        # )
        rule_name = "MyRuleCFNGuard"
        rule_dir = "rdk_rules"
        sample_policy_text = Path(f'{rule_dir}/{rule_name}/rule_code.guard').read_text()

        # sample_policy_text = """
        # rule checkcompliance when 
        #     resourceType IN ['AWS::SNS::Topic'] {
        #         awsRegion == "us-east-1"
        # }
        # """

        config.CustomPolicy(self, "CustomSnsPolicy",
            policy_text=sample_policy_text,
            enable_debug_log=True,
            rule_scope=config.RuleScope.from_resources([config.ResourceType.SNS_TOPIC])
        )