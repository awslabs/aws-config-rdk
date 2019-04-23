import sys
import unittest
try:
    from unittest.mock import MagicMock
except ImportError:
    import mock
    from mock import MagicMock
import botocore
from botocore.exceptions import ClientError
from unittest.mock import patch

##############
# Parameters #
##############

# Define the default resource to report to Config Rules
DEFAULT_RESOURCE_TYPE = 'AWS::::Account'

#############
# Main Code #
#############

CONFIG_CLIENT_MOCK = MagicMock()
STS_CLIENT_MOCK = MagicMock()

def mock_get_client(client_name, *args, **kwargs):
    if client_name == 'config':
        return CONFIG_CLIENT_MOCK
    elif client_name == 'sts':
        return STS_CLIENT_MOCK
    else:
        raise Exception("Attempting to create an unknown client")

MODULE = __import__('<%RuleName%>')
RULE = MODULE.<%RuleName%>()

class SampleTest(unittest.TestCase):

    rule_parameters = '{"SomeParameterKey":"SomeParameterValue","SomeParameterKey2":"SomeParameterValue2"}'

    invoking_event_iam_role_sample = '{"configurationItem":{"relatedEvents":[],"relationships":[],"configuration":{},"tags":{},"configurationItemCaptureTime":"2018-07-02T03:37:52.418Z","awsAccountId":"123456789012","configurationItemStatus":"ResourceDiscovered","resourceType":"AWS::IAM::Role","resourceId":"some-resource-id","resourceName":"some-resource-name","ARN":"some-arn"},"notificationCreationTime":"2018-07-02T23:05:34.445Z","messageType":"ConfigurationItemChangeNotification"}'

    def setUp(self):
        pass

    def test_sample(self):
        self.assertTrue(True)

    #def test_sample_2(self):
    #    RULE.ASSUME_ROLE_MODE = False
    #    response = RULE.lambda_handler(build_lambda_configurationchange_event(self.invoking_event_iam_role_sample, self.rule_parameters), {})
    #    resp_expected = []
    #    resp_expected.append(build_expected_response('NOT_APPLICABLE', 'some-resource-id', 'AWS::IAM::Role'))
    #    assert_successful_evaluation(self, response, resp_expected)

def sts_mock():
    assume_role_response = {
        "Credentials": {
            "AccessKeyId": "string",
            "SecretAccessKey": "string",
            "SessionToken": "string"}}
    STS_CLIENT_MOCK.reset_mock(return_value=True)
    STS_CLIENT_MOCK.assume_role = MagicMock(return_value=assume_role_response)

##################
# Common Testing #
##################

class TestStsErrors(unittest.TestCase):

    @patch('rdklib.rdklib.get_client', side_effect=botocore.exceptions.ClientError(
        {'Error': {'Code': 'InternalError', 'Message': 'InternalError'}}, 'operation'))
    def test_sts_unknown_error(self, my_mock):
        response = MODULE.lambda_handler(rdklib.build_lambda_scheduled_event(), {})
        print(response)
        rdklib.assert_customer_error_response(
            self, response, 'InternalError', 'InternalError')

    @patch('rdklib.rdklib.get_client', side_effect=botocore.exceptions.ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'AWS Config does not have permission to assume the IAM role.'}}, 'operation'))
    def test_sts_access_denied(self, my_mock):
        response = MODULE.lambda_handler(rdklib.build_lambda_scheduled_event(), {})
        print(response)
        rdklib.assert_customer_error_response(
            self, response, 'AccessDenied', 'AWS Config does not have permission to assume the IAM role.')
