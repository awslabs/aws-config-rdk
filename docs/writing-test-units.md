# Introduction

If you are creating a new rule using RDK, the `rdk create` command will automatically create a unit test script file (named with "_test" appended to your Config rule name).
If you are adding a unit test script to an existing rule, you can use `rdk create` with the same parameters like you're creating a new rule, then copy just the `*_test.py` file it creates to your existing python-code folder (you can delete any other files it creates). For example, the following command will create `MyCoolNewRule.py` and `MyCoolNewRule_test.py`, as well as a `parameters.json` file containing some metadata about your rule.

```bash
rdk create MyCoolNewRule --runtime python3.9-lib --resource-types AWS::EC2::Instance --input-parameters '{"desiredInstanceType":"t2.micro"}'
```

## Developing a unit test

Your unit tests will look very different depending on whether they are Configuration change-based or frequency-based. For Configuration change-based Config rules, you may only need to write a few sample configuration items. For frequency-based rules (or Configuration change-based rules that make boto3 calls), mock boto3 responses will need to be defined to create testing scenarios. In some cases, you will also need mock boto3 calls in change-based rules as well.

### Example (for a Frequency-based Config rule)

Frequency-based Config rules do not take a CI as a parameter. Instead, a frequency-based Config rule queries specific resources in the account to determine whether the rule is Compliant. In order to create a unit test for frequency-based Config rules, the unit test must define mock responses that will replace the actual response from boto3 during unit testing. Update the Boto3Mock definition to include any boto3 clients that your Config rule invokes.

By default, `rdk create` will create an IAM and STS mock client for you. Any additional clients must be added. This is an example that adds an EMR client:

```python
CONFIG_CLIENT_MOCK = MagicMock()
EMR_CLIENT_MOCK = MagicMock()  # Added
STS_CLIENT_MOCK = MagicMock()

class Boto3Mock():
    @staticmethod
    def client(client_name, *args, **kwargs):
        if client_name == "emr":  # Added
            return EMR_CLIENT_MOCK  # Added
        if client_name == "config":
            return CONFIG_CLIENT_MOCK
        if client_name == "sts":
            return STS_CLIENT_MOCK
        raise Exception("Attempting to create an unknown client")
```

Add your mock responses, mock event, and unit test method to the ComplianceTest class

This is an example referencing the same EMR client as defined above.

```python
class ComplianceTest(unittest.TestCase):

    # This is a dict that will act as the response for the EMR boto3 method get_block_public_access_configuration(). This content was adapted from https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/emr.html#EMR.Client.get_block_public_access_configuration.
    mock_bpa_response = {
        "BlockPublicAccessConfiguration": {
            "PermittedPublicSecurityGroupRuleRanges": [],
            "BlockPublicSecurityGroupRules": True
        }
    }

    # Some Config rules expect to be invoked with events that have certain properties on them, such as 'invokingEvent' or 'executionRoleArn'. You may need to provide dummy event values to avoid KeyErrors in your Config evaluation
    mock_event = {
        "invokingEvent": '{"awsAccountId":"123456789012","notificationCreationTime":"2016-07-13T21:50:00.373Z",'
        + '"messageType":"ScheduledNotification","recordVersion":"1.0"}',
        "ruleParameters": '{"myParameterKey":"myParameterValue"}',
        "resultToken": "myResultToken",
        "eventLeftScope": False,
        "executionRoleArn": "arn:aws:iam::dummyAccount:role/dummyRole",
        "configRuleName": "periodic-config-rule",
        "configRuleId": "config-rule-6543210",
        "accountId": "123456789012",
        "version": "1.0",
    }

    def test_mock_bpa_configured_response(self):
        sts_mock()  # This function creates mock responses for the STS client's methods (such as AssumeRole)
        # This is what tells the Mock EMR client to replace the boto3 method get_block_public_access_configuration with the mock response specified above.
        EMR_CLIENT_MOCK.get_block_public_access_configuration = MagicMock(
            return_value=self.mock_bpa_response
        )
        response = RULE.evaluate_compliance(
            self.mock_event,
            self.config_item,
            self.rule_parameters
        )
        expected_response = [
            build_expected_response(
                compliance_type="COMPLIANT",
                compliance_resource_id="test",
                compliance_resource_type=DEFAULT_RESOURCE_TYPE,
                annotation="EMR Block Public access in this account"
            )
        ]
        assert_successful_evaluation(self, response, expected_response, len(response))

```

### Example (for a Configuration change-based Config rule)

This is an example of a unit test for an API Gateway Stage. It uses a CI-based approach.

```python
class ComplianceTest(unittest.TestCase):
    test1id = "access_log_unit_test_1"
    # This is a configuration item definition that will be used to test the Config rule
    mock_ci_no_access_log_settings = {
        "resourceType": "AWS::ApiGateway::Stage",
        "resourceId": test1id,
        "configurationItemCaptureTime": "2021-10-07T04:34:52.542Z",
        "configuration": {
            "stageName": "Dev",
            "restApiId": "test",
        }
    } # Note that not all fields of an actual Configuration Item need to be included in the mock CI.

    def test_no_access_log_settings(self):
        response = RULE.evaluate_compliance({}, self.mock_ci_no_access_log_settings, {})  # Notice that the CI parameter is being provided the mock CI built above
        # Define the response you expect from your Config rule for the given CI
        expected_response = build_expected_response(
            compliance_type="NON_COMPLIANT",
            compliance_resource_id=self.test1id,
            compliance_resource_type=DEFAULT_RESOURCE_TYPE,
            annotation="AccessLogSettings are not defined for this stage."  # The exact annotation you expect should be provided.
        )
        # This function will verify that the expected and actual response match.
        assert_successful_evaluation(self, response, expected_response, len(response))

    # More unit tests can be added to the same ComplianceTest Class
    test_correct_access_log_settings = { "fillThisIn": "withRealData" }
    def test_correct_access_log_settings(self):
        # Implementation omitted for brevity

```

## Running Unit Tests

```bash
rdk test-local <name of folder containing the RDK rule>
```

## Debugging

The easiest way to debug a unit test is to add the following at the bottom of your `*_test.py` file:

```python
if __name__ == '__main__':
    unittest.main()

```

Then run your IDE's debugger (eg. 'Start Debugging' in VSCode). This will run your unit tests and stop at any breakpoints so you can see what the data looks like.
