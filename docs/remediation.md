# Remediating noncompliant resources

You can set up manual or automatic remediation for your rules to remediate noncompliant resources that are evaluated by AWS Config rules. AWS Config uses [AWS Systems Manager Automation Documents](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html) to apply remediation. You can use one of the more than 100 -pre-configured documents included in AWS Systems Manager or [create](https://docs.aws.amazon.com/systems-manager/latest/userguide/documents-creating-content.html#writing-ssm-doc-content) your own Systems Manager document to remediate non-compliant resources.

Under the hood, RDK creates an _AWS::Config::RemediationConfiguration_ CloudFormation resource and associates it with your rule when you create or modify a rule with remediation actions. To learn more about this resource view _AWS::Config::RemediationConfiguration_ - AWS CloudFormation on AWS documentations.

You can set _AWS::Config::RemediationConfiguration_ resource properties when creating or modifying a rule by including RDK rule remediation arguments. Following table includes a list of arguments that you can pass to `rdk create` or `rdk modify` to configure remediation action and how they map to _AWS::Config::RemediationConfiguration_ properties.

| `rdk create`/`rdk modify` argument | RemediationConfiguration property | Description |
| ---------------------------------- | --------------------------------- | ----------- |
| `--remediation-action` | [TargetId](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-config-remediationconfiguration.html#cfn-config-remediationconfiguration-targetid) | SSM Document name |
| `--remediation-action-version` | [TargetVersion](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-config-remediationconfiguration.html#cfn-config-remediationconfiguration-targetversion) | SSM Document version |
| `--auto-remediate` | [Automatic](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-config-remediationconfiguration.html#cfn-config-remediationconfiguration-automatic) | The remediation is triggered automatically. |
| `--auto-remediation-retry-attempts` | [MaximumAutomaticAttempts](file:///Users/nimaft/Documents/Content/Blog/MaximumAutomaticAttempts) | The maximum number of failed attempts for auto-remediation. |
| `--auto-remediation-retry-time` | [RetryAttemptSeconds](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-config-remediationconfiguration.html#cfn-config-remediationconfiguration-retryattemptseconds) | Maximum time in seconds that AWS Config runs auto-remediation. |
| `--remediation-concurrent-execution-percent` | [ExecutionControls.SsmControls.ConcurrentExecutionRatePercentage](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-config-remediationconfiguration-ssmcontrols.html#cfn-config-remediationconfiguration-ssmcontrols-concurrentexecutionratepercentage) | The maximum percentage of remediation actions allowed to run in parallel on the non-compliant resources. |
| `--remediation-error-rate-percent` | [ExecutionControls.SsmControls.ErrorPercentage](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-config-remediationconfiguration-ssmcontrols.html#cfn-config-remediationconfiguration-ssmcontrols-errorpercentage) | The percentage of errors that are allowed before SSM stops running automations on non-compliant resources. |
| `--remediation-parameters` | [Parameters](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-config-remediationconfiguration.html#cfn-config-remediationconfiguration-parameters) | SSM Document parameters. |

Some SSM Documents require input parameters to work properly. When setting up rule remediation, you can use `--remediation-parameters` to pass parameters to selected Document. This argument takes a JSON string containing Document parameters and has the following structure:

```json
{
  "SSMDocumentParameterX": {
      "StaticValue": {
          "Values": [
              "StaticValue1"
          ]
      }
  },
  "SSMDocumentParameterY": {
      "ResourceValue": {
          "Value": [
              "RESOURCE_ID"
          ]
      }
  }
}
```

Note that there are two types of values: static value and resource value. Static value can take a list of values, whereas resource value can only take one value and it should be `RESOURCE_ID`. When you pass resource value as an input parameter, the actual value is determined during runtime and it would be the resource ID of noncompliant resource evaluated by AWS Config.

Imagine you want to have a remediation action for the rule we created in previous section and delete all the noncompliant IAM Roles with no policies. First, check the list of AWS managed Document (available on the [Systems Manager console](https://console.aws.amazon.com/systems-manager/documents)) to see if a Document meeting our goal already exists. Matching our need, AWS SSM offers a managed Document named [“AWSConfigRemediation-DeleteIAMRole”](https://console.aws.amazon.com/systems-manager/documents/AWSConfigRemediation-DeleteIAMRole). Navigate to Document’s [Detail](https://console.aws.amazon.com/systems-manager/documents/AWSConfigRemediation-DeleteIAMRole/details) tab and review the required parameters. This Document requires two parameters `“AutomationAssumeRole”` and `“IAMRoleID”`. First, you need to create an IAM role for the SSM Documents to complete its steps. Review step inputs for each step of the Rule under Description tab to determine required permissions for `“AutomationAssumeRole”` Role. For `“IAMRoleID”` we are going to pass the resource ID of noncompliant resources dynamically. Finally, you can issue the following command to modify your rule and specify `“AWSConfigRemediation-DeleteIAMRole”` Document as the remediation action with its required parameters:

```bash
rdk modify IAM_ROLE --runtime python3.9 --remediation-action AWSConfigRemediation-DeleteIAMRole --remediation-parameters '{"AutomationAssumeRole":{"StaticValue":{"Values":["arn:aws:iam::123456789012:role/managed/DocumentRole"]}},"IAMRoleID":{"ResourceValue":{"Value":"RESOURCE_ID"}}}'
```

Note that the remediation actions for AWS Config Rules is only supported in certain [regions](https://docs.aws.amazon.com/config/latest/developerguide/remediation.html#region-support-config-remediation).
