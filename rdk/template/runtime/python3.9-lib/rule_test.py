import datetime
import json
import logging
import unittest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from rdklib import Evaluation, ComplianceType
import rdklibtest

##############
# Parameters #
##############

# Define the default resource to report to Config Rules
# TODO - Replace with your resource type
RESOURCE_TYPE = "AWS::IAM::Role"

#############
# Main Code #
#############

MODULE = __import__('<%RuleName%>')
RULE = MODULE.<%RuleName%>()

CLIENT_FACTORY = MagicMock()

# example for mocking IAM API calls
IAM_CLIENT_MOCK = MagicMock()
# STS client for getting account ID
STS_CLIENT_MOCK = MagicMock()


def mock_get_client(client_name, *args, **kwargs):
    if client_name == "iam":
        return IAM_CLIENT_MOCK
    if client_name == "sts":
        return STS_CLIENT_MOCK
    raise Exception("Attempting to create an unknown client")


@patch.object(CLIENT_FACTORY, "build_client", MagicMock(side_effect=mock_get_client))
class ComplianceTest(unittest.TestCase):
    rule_parameters = {
        "SomeParameterKey": "SomeParameterValue",
        "SomeParameterKey2": "SomeParameterValue2",
    }

    role_sample_configuration_abridged = {"arn": "some-arn", "roleName": "testrole"}

    invoking_event_iam_role_sample = {
        "configurationItem": {
            "relatedEvents": [],
            "relationships": [],
            "configuration": role_sample_configuration_abridged,
            "tags": {},
            "configurationItemCaptureTime": "2018-07-02T03:37:52.418Z",
            "awsAccountId": "123456789012",
            "configurationItemStatus": "ResourceDiscovered",
            "resourceType": "AWS::IAM::Role",
            "resourceId": "some-resource-id",
            "resourceName": "some-resource-name",
            "ARN": "some-arn",
        },
        "notificationCreationTime": "2018-07-02T23:05:34.445Z",
        "messageType": "ConfigurationItemChangeNotification",
        "executionRoleArn": "arn:aws:dummy",
    }

    list_roles_response = {
        "Roles": [
            {
                "Path": "/",
                "RoleName": "testrole",
                "RoleId": "some-role-id",
                "Arn": "arn:aws:iam::111111111111:role/testrole",
                "CreateDate": datetime.datetime(2015, 1, 1),
                "Description": "this is a test role",
                "MaxSessionDuration": 123,
                "Tags": [
                    {"Key": "one_tag", "Value": "its_value"},
                ],
                "RoleLastUsed": {
                    "LastUsedDate": datetime.datetime(2015, 1, 1),
                    "Region": "us-east-1",
                },
            },
        ]
    }
    test_account_id = "111111111111"
    get_caller_identity_response = {"Account": test_account_id}

    def setUp(self):
        STS_CLIENT_MOCK.reset_mock()

    def test_sample(self):
        self.assertTrue(True)

    # Example of how to evaluate a configuration change rule
    def test_configurationchange_rule(self):
        # Mock any usage of get_caller_identity
        STS_CLIENT_MOCK.get_caller_identity = MagicMock(
            return_value=self.get_caller_identity_response
        )
        response = RULE.evaluate_change(
            event=json.dumps(self.invoking_event_iam_role_sample),
            client_factory=CLIENT_FACTORY,
            configuration_item=self.role_sample_configuration_abridged,
            valid_rule_parameters=json.dumps(self.rule_parameters),
        )
        resp_expected = []
        resp_expected.append(
            Evaluation(
                complianceType=ComplianceType.NOT_APPLICABLE,
                annotation="This is a configuration change rule's annotation.",
                resourceId=self.invoking_event_iam_role_sample.get(
                    "configurationItem", {}
                ).get("resourceId", None),
                resourceType=RESOURCE_TYPE,
            )
        )
        if vars(response[0]) != vars(resp_expected[0]):
            logging.warning(f"Actual response: {vars(response[0])}")
            logging.warning(f"Expected response: {vars(resp_expected[0])}")
        rdklibtest.assert_successful_evaluation(self, response, resp_expected)

    # Example of how to mock the client response for a list_roles API call
    def test_periodic_rule(self):
        # Mock any usage of get_caller_identity
        STS_CLIENT_MOCK.get_caller_identity = MagicMock(
            return_value=self.get_caller_identity_response
        )
        IAM_CLIENT_MOCK.list_roles = MagicMock(return_value=self.list_roles_response)
        # Example of how to evaluate a periodic rule
        response = RULE.evaluate_periodic(
            event=rdklibtest.create_test_scheduled_event(self.rule_parameters),
            client_factory=CLIENT_FACTORY,
            valid_rule_parameters=json.dumps(self.rule_parameters),
        )
        resp_expected = []
        resp_expected.append(
            Evaluation(
                complianceType=ComplianceType.NOT_APPLICABLE,
                resourceId=self.invoking_event_iam_role_sample.get(
                    "configurationItem", {}
                ).get("awsAccountId", None),
                resourceType="AWS::::Account",
                annotation="This is a periodic rule's annotation.",
            )
        )
        if vars(response[0]) != vars(resp_expected[0]):
            logging.warning(f"Actual response: {vars(response[0])}")
            logging.warning(f"Expected response: {vars(resp_expected[0])}")
        rdklibtest.assert_successful_evaluation(self, response, resp_expected)


if __name__ == "__main__":
    unittest.main()
