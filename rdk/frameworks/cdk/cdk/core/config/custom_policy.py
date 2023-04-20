import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aws_cdk import aws_config as config

from ..errors import RdkParametersInvalidError


@dataclass
class CustomPolicy:
    """
    Defines Custom Policy.

    Parameters:

    * **`policy_text`** (_str_): The policy definition containing the logic for your AWS Config Custom Policy rule.
    * **`enable_debug_log`** (_bool_): Optional - The boolean expression for enabling debug logging for your AWS Config Custom Policy rule. Default: false
    * **`config_rule_name`** (_str_): A name for the AWS Config rule. Default: - CloudFormation generated name
    * **`description`** (_str_): Optional - A description about this AWS Config rule. Default: - No description
    * **`input_parameters`** (_Dict[str, Any]_): Optional - Input parameter values that are passed to the AWS Config rule. Default: - No input parameters
    * **`maximum_execution_frequency`** (_MaximumExecutionFrequency_): Optional - The maximum frequency at which the AWS Config rule runs evaluations.
    * **`rule_scope`** (_RuleScope_): Optional - Defines which resources trigger an evaluation for an AWS Config rule. Default: - evaluations for the rule are triggered when any resource in the recording group changes.

    """

    policy_text: str = field(init=False)
    enable_debug_log: Optional[bool] = False
    config_rule_name: str = field(init=False)
    description: Optional[str] = None
    input_parameters: Optional[Dict[str, Any]] = None
    maximum_execution_frequency: Optional[config.MaximumExecutionFrequency] = None
    rule_scope: Optional[config.RuleScope] = None

    def __init__(self, policy_text: str, rule_parameters: dict):
        param = rule_parameters["Parameters"]
        self.policy_text = policy_text
        if "RuleName" in param:
            self.config_rule_name = param["RuleName"]
        if "EnableDebugLogDelivery" in param:
            self.enable_debug_log = True
        if "Description" in param:
            self.description = param["Description"]
        if "InputParameters" in param:
            self.input_parameters = json.loads(param["InputParameters"])
        if "MaximumExecutionFrequency" in param:
            try:
                maximum_execution_frequency = getattr(config.MaximumExecutionFrequency, param["SourcePeriodic"].upper())
            except:
                raise RdkParametersInvalidError("Invalid parameters found in Parameters.MaximumExecutionFrequency. Please review https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-config-configrule.html#cfn-config-configrule-maximumexecutionfrequency")                
            self.maximum_execution_frequency = maximum_execution_frequency
        if "SourceEvents" in param:
            try:
                source_events = getattr(config.ResourceType, param["SourceEvents"].upper().replace("AWS::", "").replace("::", "_"))
            except:
                raise RdkParametersInvalidError("Invalid parameters found in Parameters.SourceEvents. Please review https://docs.aws.amazon.com/config/latest/developerguide/resource-config-reference.html")                
            self.rule_scope = config.RuleScope.from_resources([source_events])
