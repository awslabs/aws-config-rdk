# Copyright 2017-2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may
# not use this file except in compliance with the License. A copy of the License is located at
#
#        http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
# the specific language governing permissions and limitations under the License.

import unittest
from mock import mock, MagicMock
from rdklib import rdklib

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

CONFIG_CLIENT_MOCK = MagicMock()
STS_CLIENT_MOCK = MagicMock()

def mock_get_client(client_name, *args, **kwargs):
    if client_name == 'config':
        return CONFIG_CLIENT_MOCK
    if client_name == 'sts':
        return STS_CLIENT_MOCK
    raise Exception("Attempting to create an unknown client")

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
