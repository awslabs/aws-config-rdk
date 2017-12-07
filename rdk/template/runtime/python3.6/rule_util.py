#
# This file made available under CC0 1.0 Universal (https://creativecommons.org/publicdomain/zero/1.0/legalcode)
#

import json
import boto3
import datetime

# USE ENTIRE FILE AS IS

aws_config = boto3.client('config')

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
    return (status == 'OK' or status == 'ResourceDiscovered') and eventLeftScope == False

# This decorates the lambda_handler in rule_code with the actual PutEvaluation call
def rule_handler(lambda_handler):
    def handler_wrapper(event, context):
        #print(event)
        check_defined(event, 'event')
        invokingEvent = json.loads(event['invokingEvent'])
        ruleParameters = {}
        if 'ruleParameters' in event:
            ruleParameters = json.loads(event['ruleParameters'])
        configurationItem = get_configuration_item(invokingEvent)
        if configurationItem is None:
            print("RDK utility class does not yet support Scheduled Notifications.")
            return ("Not_Applicable")
        invokingEvent['configurationItem'] = configurationItem
        event['invokingEvent'] = json.dumps(invokingEvent)
        compliance = 'NOT_APPLICABLE'
        if is_applicable(configurationItem, event):
            # Invoke the compliance checking function.
            compliance = lambda_handler(event, context)
        # Put together the request that reports the evaluation status
        evaluations = [{
                'ComplianceResourceType': configurationItem['resourceType'],
                'ComplianceResourceId': configurationItem['resourceId'],
                'ComplianceType': compliance,
                'OrderingTimestamp': configurationItem['configurationItemCaptureTime']
        }]
        resultToken = event['resultToken']
        testMode = False
        if resultToken == 'TESTMODE':
            # Used solely for RDK test to skip actual put_evaluation API call
            testMode = True
        # Invoke the Config API to report the result of the evaluation
        aws_config.put_evaluations(Evaluations=evaluations, ResultToken=resultToken, TestMode=testMode)
        # Used solely for RDK test to be able to test Lambda function
        return compliance
    return handler_wrapper
