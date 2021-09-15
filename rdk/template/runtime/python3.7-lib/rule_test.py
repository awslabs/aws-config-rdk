import unittest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
import rdklib
from rdklib import Evaluation, ComplianceType
import rdklibtest

##############
# Parameters #
##############

# Define the default resource to report to Config Rules
RESOURCE_TYPE = 'AWS::::Account'

#############
# Main Code #
#############

MODULE = __import__('<%RuleName%>')
RULE = MODULE.<%RuleName%>()

CLIENT_FACTORY = MagicMock()

#example for mocking S3 API calls
S3_CLIENT_MOCK = MagicMock()

def mock_get_client(client_name, *args, **kwargs):
    if client_name == 's3':
        return S3_CLIENT_MOCK
    raise Exception("Attempting to create an unknown client")

@patch.object(CLIENT_FACTORY, 'build_client', MagicMock(side_effect=mock_get_client))
class ComplianceTest(unittest.TestCase):

    rule_parameters = '{"SomeParameterKey":"SomeParameterValue","SomeParameterKey2":"SomeParameterValue2"}'

    invoking_event_iam_role_sample = '{"configurationItem":{"relatedEvents":[],"relationships":[],"configuration":{},"tags":{},"configurationItemCaptureTime":"2018-07-02T03:37:52.418Z","awsAccountId":"123456789012","configurationItemStatus":"ResourceDiscovered","resourceType":"AWS::IAM::Role","resourceId":"some-resource-id","resourceName":"some-resource-name","ARN":"some-arn"},"notificationCreationTime":"2018-07-02T23:05:34.445Z","messageType":"ConfigurationItemChangeNotification"}'

    def setUp(self):
        pass

    def test_sample(self):
        self.assertTrue(True)

    #def test_sample_2(self):
    #    response = MODULE.lambda_handler(rdklib.build_lambda_configurationchange_event(self.invoking_event_iam_role_sample, self.rule_parameters), {})
    #    resp_expected = []
    #    resp_expected.append(rdklib.build_expected_response('NOT_APPLICABLE', 'some-resource-id', 'AWS::IAM::Role'))
    #    rdklib.assert_successful_evaluation(self, response, resp_expected)
