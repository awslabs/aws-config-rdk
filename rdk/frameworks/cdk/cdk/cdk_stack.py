from aws_cdk import (
    Stack,
    aws_config as config,
    aws_lambda as lambda_,
)
from constructs import Construct
from pathlib import Path
from .core.rule_parameters import get_rule_parameters, get_deploy_rules_list, get_rule_name, rdk_supported_custom_rule_runtime
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
                policy_text = rule_path.joinpath("rule_code.guard").read_text()

                try:
                    source_events = getattr(config.ResourceType, rule_parameters["Parameters"]["SourceEvents"].upper().replace("AWS::", "").replace("::", "_"))
                except:
                    raise RdkParametersInvalidError("Invalid parameters found in Parameters.SourceEvents. Please review https://docs.aws.amazon.com/config/latest/developerguide/resource-config-reference.html")
                
                config.CustomPolicy(self, rule_name,
                    policy_text=policy_text,
                    enable_debug_log=True,
                    rule_scope=config.RuleScope.from_resources([source_events])
                )
            elif rule_parameters["Parameters"]["SourceIdentifier"]:
                try:
                    source_identifier = getattr(config.ManagedRuleIdentifiers, rule_parameters["Parameters"]["SourceIdentifier"].upper().replace("-", "_"))
                except:
                    raise RdkParametersInvalidError("Invalid parameters found in Parameters.SourceIdentifier. Please review https://docs.aws.amazon.com/config/latest/developerguide/managed-rules-by-aws-config.html")

                try:
                    source_events = getattr(config.ResourceType, rule_parameters["Parameters"]["SourceEvents"].upper().replace("AWS::", "").replace("::", "_"))
                except:
                    raise RdkParametersInvalidError("Invalid parameters found in Parameters.SourceEvents. Please review https://docs.aws.amazon.com/config/latest/developerguide/resource-config-reference.html")
                
                config.ManagedRule(self, rule_name,
                    identifier=source_identifier,
                    input_parameters={
                        "max_access_key_age": 60
                    },
                    rule_scope=config.RuleScope.from_resources([source_events])
                )
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