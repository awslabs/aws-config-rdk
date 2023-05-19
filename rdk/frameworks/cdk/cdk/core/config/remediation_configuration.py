import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from aws_cdk import aws_config as config
from aws_cdk import IResolvable

from ..errors import RdkParametersInvalidError


@dataclass
class RemediationConfiguration:
    """
    Defines AWS Config Rule Remediation Configuration.

    Parameters:

    * **`config_rule_name `** (_str_): The name of the AWS Config rule.
    * **`target_id `** (_str_): Target ID is the name of the SSM document.
    * **`target_type `** (_str_): The type of the target. Target executes remediation. For example, SSM document.
    * **`automatic`** (_Union[bool, IResolvable, None]_) : Optional - The remediation is triggered automatically.
    * **`execution_controls`** (_Union[IResolvable, ExecutionControlsProperty, Dict[str, Any], None]_) : Optional - An ExecutionControls object.
    * **`maximum_automatic_attempts`** (_Union[int, float, None]_) : Optional - The maximum number of failed attempts for auto-remediation. If you do not select a number, the default is 5. For example, if you specify MaximumAutomaticAttempts as 5 with RetryAttemptSeconds as 50 seconds, AWS Config will put a RemediationException on your behalf for the failing resource after the 5th failed attempt within 50 seconds.
    * **`parameters`** (_Optional[Any]_) : Optional - An object of the RemediationParameterValue. For more information, see RemediationParameterValue . .. epigraph:: The type is a map of strings to RemediationParameterValue.
    * **`resource_type`** (_Optional[str]_) : Optional - The type of a resource.
    * **`retry_attempt_seconds`** (_Union[int, float, None]_) : Optional - Maximum time in seconds that AWS Config runs auto-remediation. If you do not select a number, the default is 60 seconds. For example, if you specify RetryAttemptSeconds as 50 seconds and MaximumAutomaticAttempts as 5, AWS Config will run auto-remediations 5 times within 50 seconds before throwing an exception.
    * **`target_version`** (_Optional[str]_) : Optional - Version of the target. For example, version of the SSM document. .. epigraph:: If you make backward incompatible changes to the SSM document, you must call PutRemediationConfiguration API again to ensure the remediations can run.


    """

    config_rule_name: str = field(init=False)
    target_id: str = field(init=False)
    target_type: str = field(init=False)
    automatic: Optional[Union[bool, IResolvable, None]] = None
    execution_controls: Optional[
        Union[
            IResolvable,
            config.CfnRemediationConfiguration.ExecutionControlsProperty,
            Dict[str, Any],
            None,
        ]
    ] = None
    maximum_automatic_attempts: Optional[Union[int, float, None]] = None
    parameters: Optional[Any] = None
    resource_type: Optional[str] = None
    retry_attempt_seconds: Union[int, float, None] = None
    target_version: Optional[str] = None

    def __init__(self, rule_parameters: dict):
        param = rule_parameters["Parameters"]
        reme_param = param["Remediation"]
        self.target_id = reme_param["TargetId"]
        self.target_type = reme_param["TargetType"]
        if "RuleName" in rule_parameters["Parameters"]:
            self.config_rule_name = rule_parameters["Parameters"]["RuleName"]
        if "Automatic" in reme_param:
            self.automatic = reme_param["Automatic"]
        if "ExecutionControls" in reme_param:
            if "SsmControls" in reme_param["ExecutionControls"]:
                if (
                    "ConcurrentExecutionRatePercentage"
                    in reme_param["ExecutionControls"]["SsmControls"]
                ):
                    concurrent_execution_rate_percentage = reme_param[
                        "ExecutionControls"
                    ]["SsmControls"]["ConcurrentExecutionRatePercentage"]
                if "ErrorPercentage" in reme_param["ExecutionControls"]["SsmControls"]:
                    error_percentage = reme_param["ExecutionControls"]["SsmControls"][
                        "ErrorPercentage"
                    ]
                ssm_controls = config.CfnRemediationConfiguration.SsmControlsProperty(
                    concurrent_execution_rate_percentage=concurrent_execution_rate_percentage,
                    error_percentage=error_percentage,
                )
            self.execution_controls = (
                config.CfnRemediationConfiguration.ExecutionControlsProperty(
                    ssm_controls
                )
            )
        if "MaximumAutomaticAttempts" in reme_param:
            self.maximum_automatic_attempts = int(
                reme_param["MaximumAutomaticAttempts"]
            )
        if "Parameters" in reme_param:
            self.parameters = reme_param["Parameters"]
        if "ResourceType" in reme_param:
            self.resource_type = reme_param["ResourceType"]
        if "RetryAttemptSeconds" in reme_param:
            self.retry_attempt_seconds = int(reme_param["RetryAttemptSeconds"])
        if "TargetVersion" in reme_param:
            self.target_version = reme_param["TargetVersion"]
