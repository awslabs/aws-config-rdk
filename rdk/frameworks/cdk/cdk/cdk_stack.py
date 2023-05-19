import json
import uuid
from dataclasses import asdict
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import Stack
from aws_cdk import aws_config as config
from aws_cdk import aws_lambda as lambda_
from constructs import Construct

from .core.config.custom_policy import CustomPolicy
from .core.config.custom_rule import CustomRule
from .core.config.managed_rule import ManagedRule
from .core.config.lambda_function import LambdaFunction
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
            print(f"Adding Rule {rule_name} ...")
            if "SourceRuntime" in rule_parameters["Parameters"] and rule_parameters[
                "Parameters"
            ]["SourceRuntime"] in ["cloudformation-guard2.0", "guard-2.x.x"]:
                arg = CustomPolicy(
                    policy_text=rule_path.joinpath("rule_code.guard").read_text(),
                    rule_parameters=rule_parameters,
                )
                config.CustomPolicy(self, rule_name, **asdict(arg))
            elif (
                "SourceRuntime" in rule_parameters["Parameters"]
                and rule_parameters["Parameters"]["SourceRuntime"]
                in rdk_supported_custom_rule_runtime
            ):
                # Lambda function containing logic that evaluates compliance with the rule.
                fn_arg = LambdaFunction(
                    code=lambda_.Code.from_asset(rule_path.as_posix()),
                    rule_parameters=rule_parameters,
                )
                if "-lib" in rule_parameters["Parameters"]["SourceRuntime"]:
                    layer_version_arn = (
                        fn_arg.get_latest_rdklib_lambda_layer_version_arn()
                    )
                    latest_layer = lambda_.LayerVersion.from_layer_version_arn(
                        scope=self,
                        id="rdklayerversion",
                        layer_version_arn=layer_version_arn,
                    )
                    # fn_arg.layers.append(latest_layer)
                eval_compliance_fn = lambda_.Function(
                    self,
                    f"{rule_name}Function",
                    **asdict(fn_arg),
                    layers=[latest_layer],
                )

                # A custom rule that runs on configuration changes of EC2 instances
                arg = CustomRule(
                    lambda_function=eval_compliance_fn, rule_parameters=rule_parameters
                )
                config.CustomRule(self, rule_name, **asdict(arg))
            elif (
                "SourceIdentifier" in rule_parameters["Parameters"]
                and rule_parameters["Parameters"]["SourceIdentifier"]
            ):
                arg = ManagedRule(rule_parameters=rule_parameters)
                config.ManagedRule(self, rule_name, **asdict(arg))
            else:
                print(f"Rule type not supported for Rule {rule_name}")
                continue
                # raise RdkRuleTypesInvalidError(f"Error loading parameters file for Rule {rule_name}")

            if (
                "Remediation" in rule_parameters["Parameters"]
                and rule_parameters["Parameters"]["Remediation"]
            ):
                arg = RemediationConfiguration(rule_parameters=rule_parameters)
                config.CfnRemediationConfiguration(
                    self, f"{rule_name}RemediationConfiguration", **asdict(arg)
                )
            # # A rule to detect stack drifts
            # drift_rule = config.CloudFormationStackDriftDetectionCheck(self, "Drift")

            # # Topic to which compliance notification events will be published
            # compliance_topic = sns.Topic(self, "ComplianceTopic")

            # # Send notification on compliance change events
            # drift_rule.on_compliance_change("ComplianceChange",
            #     target=targets.SnsTopic(compliance_topic)
            # )
