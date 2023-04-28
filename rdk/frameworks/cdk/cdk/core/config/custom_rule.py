import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aws_cdk import aws_config as config
from aws_cdk import aws_lambda as _lambda

from ..errors import RdkParametersInvalidError


@dataclass
class CustomRule:
    """
    Defines AWS Config Custom Rule.

    Parameters:

    * **`lambda_function`** (_IFunction) – The Lambda function to run.
    * **`configuration_changes`** (_Optional[bool]_): Optional - Whether to run the rule on configuration changes. Default: false
    * **`periodic`** (_Optional[bool]_): Optional - Whether to run the rule on a fixed frequency. Default: false
    * **`config_rule_name`** (_str_): A name for the AWS Config rule. Default: - CloudFormation generated name
    * **`description`** (_str_): Optional - A description about this AWS Config rule. Default: - No description
    * **`input_parameters`** (_Dict[str, Any]_): Optional - Input parameter values that are passed to the AWS Config rule. Default: - No input parameters
    * **`maximum_execution_frequency`** (_MaximumExecutionFrequency_): Optional - The maximum frequency at which the AWS Config rule runs evaluations.
    * **`rule_scope`** (_RuleScope_): Optional - Defines which resources trigger an evaluation for an AWS Config rule. Default: - evaluations for the rule are triggered when any resource in the recording group changes.



    """

    lambda_function: _lambda.IFunction = field(init=False)
    configuration_changes: Optional[bool] = None
    periodic: Optional[bool] = None
    config_rule_name: str = field(init=False)
    description: Optional[str] = None
    input_parameters: Optional[Dict[str, Any]] = None
    maximum_execution_frequency: Optional[config.MaximumExecutionFrequency] = None
    rule_scope: Optional[config.RuleScope] = None

    def __init__(self, lambda_function: _lambda.IFunction, rule_parameters: dict):
        param = rule_parameters["Parameters"]
        self.lambda_function = lambda_function
        if "SourcePeriodic" in param:
            self.periodic = True
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
                self.maximum_execution_frequency = getattr(
                    config.MaximumExecutionFrequency, param["SourcePeriodic"].upper()
                )
            except:
                raise RdkParametersInvalidError(
                    "Invalid parameters found in Parameters.MaximumExecutionFrequency. Please review https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-config-configrule.html#cfn-config-configrule-maximumexecutionfrequency"
                )
        if "SourceEvents" in param:
            try:
                self.configuration_changes = True
                source_events = getattr(
                    config.ResourceType,
                    param["SourceEvents"]
                    .upper()
                    .replace("AWS::", "")
                    .replace("::", "_"),
                )
            except:
                raise RdkParametersInvalidError(
                    "Invalid parameters found in Parameters.SourceEvents. Please review https://docs.aws.amazon.com/config/latest/developerguide/resource-config-reference.html"
                )
            self.rule_scope = config.RuleScope.from_resources([source_events])
