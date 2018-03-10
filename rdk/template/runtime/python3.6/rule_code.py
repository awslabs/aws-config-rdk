#    Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
#
#        http://aws.amazon.com/apache2.0/
#
#    or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

import json
import boto3
import botocore
import datetime

aws_config = boto3.client('config')

def evaluate_compliance(configuration_item, rule_parameters):

    ###############################
    # Add your custom logic here. #
    ###############################

    return 'NOT_APPLICABLE'

# USE AS IS
# Helper function to check if rule parameters exist
def parameters_exist(parameters):
    return len(parameters) != 0

# Helper function used to validate input
def check_defined(reference, referenceName):
    if not reference:
        raise Exception('Error: ', referenceName, 'is not defined')
    return reference

# Check whether the message is OversizedConfigurationItemChangeNotification or not
def is_oversized_changed_notification(messageType):
    check_defined(messageType, 'messageType')
    return messageType == 'OversizedConfigurationItemChangeNotification'

# Check whether the message is a ScheduledNotification or not.
def is_scheduled_notification(messageType):
    check_defined(messageType, 'messageType')
    return messageType == 'ScheduledNotification'

# Get configurationItem using getResourceConfigHistory API. in case of OversizedConfigurationItemChangeNotification
def get_configuration(resourceType, resourceId, configurationCaptureTime):
    result = aws_config.get_resource_config_history(
        resourceType=resourceType,
        resourceId=resourceId,
        laterTime=configurationCaptureTime,
        limit=1)
    configurationItem = result['configurationItems'][0]
    return convert_api_configuration(configurationItem)

# Convert from the API model to the original invocation model
def convert_api_configuration(configurationItem):
    for k, v in configurationItem.items():
        if isinstance(v, datetime.datetime):
            configurationItem[k] = str(v)
    configurationItem['awsAccountId'] = configurationItem['accountId']
    configurationItem['ARN'] = configurationItem['arn']
    configurationItem['configurationStateMd5Hash'] = configurationItem['configurationItemMD5Hash']
    configurationItem['configurationItemVersion'] = configurationItem['version']
    configurationItem['configuration'] = json.loads(configurationItem['configuration'])
    if 'relationships' in configurationItem:
        for i in range(len(configurationItem['relationships'])):
            configurationItem['relationships'][i]['name'] = configurationItem['relationships'][i]['relationshipName']
    return configurationItem

# Based on the type of message get the configuration item either from configurationItem in the invoking event or using the getResourceConfigHistiry API in getConfiguration function.
def get_configuration_item(invokingEvent):
    check_defined(invokingEvent, 'invokingEvent')
    if is_oversized_changed_notification(invokingEvent['messageType']):
        configurationItemSummary = check_defined(invokingEvent['configurationItemSummary'], 'configurationItemSummary')
        return get_configuration(configurationItemSummary['resourceType'], configurationItemSummary['resourceId'], configurationItemSummary['configurationItemCaptureTime'])
    elif is_scheduled_notification(invokingEvent['messageType']):
        return None
    else:
        return check_defined(invokingEvent['configurationItem'], 'configurationItem')

# Check whether the resource has been deleted. If it has, then the evaluation is unnecessary.
def is_applicable(configurationItem, event):
    check_defined(configurationItem, 'configurationItem')
    check_defined(event, 'event')
    status = configurationItem['configurationItemStatus']
    eventLeftScope = event['eventLeftScope']
    if(status == 'ResourceDeleted'):
        print("Resource Deleted, setting Compliance Status to NOT_APPLICABLE.")
    return (status == 'OK' or status == 'ResourceDiscovered') and eventLeftScope == False

#Get role credentials that will work in either custom or managed rules.
def get_assume_role_credentials(role_arn):
    try:
        assume_role_response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName="configLambdaExecution")
        return assume_role_response['Credentials']
    except botocore.exceptions.ClientError as ex:
        # Scrub error message for any internal account info leaks
        if 'AccessDenied' in ex.response['Error']['Code']:
            ex.response['Error']['Message'] = "AWS Config does not have permission to assume the IAM role."
        else:
            ex.response['Error']['Message'] = "InternalError"
            ex.response['Error']['Code'] = "InternalError"
        raise ex

# This decorates the lambda_handler in rule_code with the actual PutEvaluation call
def lambda_handler(event, context):
    #Local method to get appropriate Boto3 client regardless of execution environment.
    def get_client(service):
        credentials = get_assume_role_credentials(event['executionRoleArn'])
        return boto3.client(
            service,
            aws_access_key_id = credentials['AccessKeyId'],
            aws_secret_access_key = credentials['SecretAccessKey'],
            aws_session_token = credentials['SessionToken'])

    evaluations = []

    #print(event)
    check_defined(event, 'event')
    invokingEvent = json.loads(event['invokingEvent'])
    rule_parameters = {}
    if 'ruleParameters' in event:
        rule_parameters = json.loads(event['ruleParameters'])

    configuration_item = get_configuration_item(invokingEvent)

    compliance_result = evaluate_compliance(configuration_item, rule_parameters)

    if isinstance(compliance_result, str):
        evaluations = [{
                'ComplianceResourceType': configuration_item['resourceType'],
                'ComplianceResourceId': configuration_item['resourceId'],
                'ComplianceType': compliance_result,
                'OrderingTimestamp': configuration_item['configurationItemCaptureTime']
        }]
    elif isinstance(compliance_result, list):
        for evaluation in compliance_result:
            missing_fields = False
            for field in ('ComplianceResourceType', 'ComplianceResourceId', 'ComplianceType', 'OrderingTimestamp'):
                if field not in evaluation:
                    print("Missing " + field + " from custom evaluation.")
                    missing_fields = True

            if not missing_fields:
                evaluations.append(evaluation)
    else:
        evaluations = [{
                'ComplianceResourceType': configuration_item['resourceType'],
                'ComplianceResourceId': configuration_item['resourceId'],
                'ComplianceType': 'NOT_APPLICABLE',
                'OrderingTimestamp': configuration_item['configurationItemCaptureTime']
        }]


    # Put together the request that reports the evaluation status
    resultToken = event['resultToken']
    testMode = False
    if resultToken == 'TESTMODE':
        # Used solely for RDK test to skip actual put_evaluation API call
        testMode = True
    # Invoke the Config API to report the result of the evaluation
    aws_config.put_evaluations(Evaluations=evaluations, ResultToken=resultToken, TestMode=testMode)
    # Used solely for RDK test to be able to test Lambda function
    #return evaluations
