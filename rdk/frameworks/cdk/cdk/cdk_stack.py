from aws_cdk import (
    Stack,
    aws_config as config,
    aws_lambda as lambda_,
)
from dataclasses import asdict
from constructs import Construct
from pathlib import Path
from .core.rule_parameters import get_rule_parameters, get_deploy_rules_list, get_rule_name, rdk_supported_custom_rule_runtime
from .core.custom_policy import CustomPolicy
from .core.managed_rule import ManagedRule
from .core.errors import RdkRuleTypesInvalidError, RdkParametersInvalidError
import json

class CdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        rules_dir = Path(self.node.try_get_context("rules_dir"))
        rules_list = get_deploy_rules_list(rules_dir)

        for rule_path in rules_list:
            rule_name = get_rule_name(rule_path)
            rule_parameters = get_rule_parameters(rule_path)

            if rule_parameters["Parameters"]["SourceRuntime"] == "cloudformation-guard2.0":
                arg = CustomPolicy(policy_text=rule_path.joinpath("rule_code.rules").read_text(), rule_parameters=rule_parameters)
                config.CustomPolicy(self, rule_name, **asdict(arg))
            elif rule_parameters["Parameters"]["SourceIdentifier"]:
                arg = ManagedRule(rule_parameters=rule_parameters)
                config.ManagedRule(self, rule_name, **asdict(arg))
            # elif rule_parameters["Parameters"]["SourceRuntime"] in rdk_supported_custom_rule_runtime:
            #     # Lambda function containing logic that evaluates compliance with the rule.
            #     eval_compliance_fn = lambda_.Function(self, "CustomFunction",
            #         code=lambda_.Code.asset(Path(self.node.try_get_context("rules_dir"))),
            #         handler="index.handler",
            #         runtime=lambda_.Runtime.NODEJS_14_X
            #     )

            #     # A custom rule that runs on configuration changes of EC2 instances
            #     config.CustomRule(self, "Custom",
            #         configuration_changes=True,
            #         lambda_function=eval_compliance_fn,
            #         rule_scope=config.RuleScope.from_resource(config.ResourceType.EC2_INSTANCE)
            #     )
            else:
                raise RdkRuleTypesInvalidError(f"Error loading parameters file for Rule {rule_name}")

            # # A rule to detect stack drifts
            # drift_rule = config.CloudFormationStackDriftDetectionCheck(self, "Drift")

            # # Topic to which compliance notification events will be published
            # compliance_topic = sns.Topic(self, "ComplianceTopic")

            # # Send notification on compliance change events
            # drift_rule.on_compliance_change("ComplianceChange",
            #     target=targets.SnsTopic(compliance_topic)
            # )