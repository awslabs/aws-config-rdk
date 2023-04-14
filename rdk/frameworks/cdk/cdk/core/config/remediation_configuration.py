import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from aws_cdk import aws_config as config
from aws_cdk import IResolvable

from ..errors import RdkParametersInvalidError


@dataclass
class RemediationConfiguration:
    """
    Defines Remediation Configuration.

    Parameters:

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
    target_id: str = field(init=False)
    target_type: str = field(init=False)
    automatic: Optional[Union[bool, IResolvable, None]] = None
    execution_controls: Optional[Union[IResolvable, config.CfnRemediationConfiguration.ExecutionControlsProperty, Dict[str, Any], None]] = None
    maximum_automatic_attempts: Optional[Union[int, float, None]] = None
    parameters: Optional[Any] = None
    resource_type: Optional[str] = None
    retry_attempt_seconds: Union[int, float, None] = None
    target_version: Optional[str] = None


    def __init__(self, rule_parameters: dict):
        param = rule_parameters["Parameters"]['Remediation']
        self.target_id = param["TargetId"]
        self.target_type = param["TargetType"]
        if "Automatic" in param:
            self.automatic = param["Automatic"]
        if "ExecutionControls" in param:
            if "SsmControls" in param["ExecutionControls"]:
                if "ConcurrentExecutionRatePercentage" in param["ExecutionControls"]["SsmControls"]:
                    concurrent_execution_rate_percentage = param["ExecutionControls"]["SsmControls"]["ConcurrentExecutionRatePercentage"]
                if "ErrorPercentage" in param["ExecutionControls"]["SsmControls"]:
                    error_percentage = param["ExecutionControls"]["SsmControls"]["ErrorPercentage"]
                ssm_controls = config.CfnRemediationConfiguration.SsmControlsProperty(
                    concurrent_execution_rate_percentage=concurrent_execution_rate_percentage,
                    error_percentage=error_percentage
                )
            self.execution_controls = config.CfnRemediationConfiguration.ExecutionControlsProperty(ssm_controls)
        if "MaximumAutomaticAttempts" in param:
            self.maximum_automatic_attempts = int(param["MaximumAutomaticAttempts"])
        if "Parameters" in param:
            self.parameters = param["Parameters"]
        if "ResourceType" in param:
            self.resource_type = param["ResourceType"]
        if "RetryAttemptSeconds" in param:
            self.retry_attempt_seconds = int(param["RetryAttemptSeconds"])
        if "TargetVersion" in param:
            self.target_version = param["TargetVersion"]
