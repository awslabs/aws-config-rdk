import json
from dataclasses import asdict
from pathlib import Path

from aws_cdk import Stack
from aws_cdk import aws_config as config
from aws_cdk import aws_lambda as lambda_
from constructs import Construct

from .core.config.custom_policy import CustomPolicy
from .core.config.managed_rule import ManagedRule
from .core.config.remediation_configuration import RemediationConfiguration

from .core.errors import RdkParametersInvalidError, RdkRuleTypesInvalidError
from .core.rule_parameters import (
    get_deploy_rules_list,
    get_rule_name,
    get_rule_parameters,
    rdk_supported_custom_rule_runtime,
)


class CdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        rules_dir = Path(self.node.try_get_context("rules_dir"))
        rules_list = get_deploy_rules_list(rules_dir)

        for rule_path in rules_list:
            rule_name = get_rule_name(rule_path)
            rule_parameters = get_rule_parameters(rule_path)

            if "SourceRuntime" in rule_parameters["Parameters"] and rule_parameters["Parameters"]["SourceRuntime"] in ["cloudformation-guard2.0", "guard-2.x.x"]:
                arg = CustomPolicy(policy_text=rule_path.joinpath("rule_code.guard").read_text(), rule_parameters=rule_parameters, config_rule_name = rule_name)
                config.CustomPolicy(self, rule_name, **asdict(arg)).config_rule_name
            elif "SourceIdentifier" in rule_parameters["Parameters"] and rule_parameters["Parameters"]["SourceIdentifier"]:
                arg = ManagedRule(rule_parameters=rule_parameters, config_rule_name = rule_name)
                config.ManagedRule(self, rule_name, **asdict(arg)).config_rule_name
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
                print(f"Rule type not supported for Rule {rule_name}")
                continue
                # raise RdkRuleTypesInvalidError(f"Error loading parameters file for Rule {rule_name}")
            
            if "Remediation" in rule_parameters["Parameters"] and rule_parameters["Parameters"]["Remediation"]:
                arg = RemediationConfiguration(rule_parameters=rule_parameters, config_rule_name = rule_name)
                config.CfnRemediationConfiguration(self, "MyCfnRemediationConfiguration", **asdict(arg))
            # # A rule to detect stack drifts
            # drift_rule = config.CloudFormationStackDriftDetectionCheck(self, "Drift")

            # # Topic to which compliance notification events will be published
            # compliance_topic = sns.Topic(self, "ComplianceTopic")

            # # Send notification on compliance change events
            # drift_rule.on_compliance_change("ComplianceChange",
            #     target=targets.SnsTopic(compliance_topic)
            # )