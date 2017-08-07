## This file made available under CC0 1.0 Universal (https://creativecommons.org/publicdomain/zero/1.0/legalcode)#
# This example rule checks that EC2 instances are EBS optimized (optionally checks that ebsOptimized field is
# equal to value passed in parameter)
#
# Trigger Type: Change Triggered# Scope of Changes: AWS::EC2::Instance# Required Parameters: None# Optional Parameter: Parameter1 # Optional Parameter value example : True

import json
import boto3
from rule_util import *

aws_config = boto3.client('config')

# CHANGES NEEDED: Replace with applicable resources for your rule
APPLICABLE_RESOURCES = ["AWS::EC2::Instance"]

# CHANGED NEEDED
# Modify, add or remove rule parameters in rdk/rules/ruleCode/ruleParameters.txt
def is_non_compliant(configuration_item, rule_parameters):
    if parameters_exist(rule_parameters):
        return check_parameters(configuration_item, rule_parameters)
    return str(configuration_item['configuration']['ebsOptimized']) != True

# CHANGES NEEDED
def check_parameters(configuration_item, rule_parameters):
    expectEbsOptimized = rule_parameters['parameter1']
    return str(configuration_item['configuration']['ebsOptimized']) != expectEbsOptimized

def evaluate_compliance(configuration_item, rule_parameters):
    if is_not_applicable(configuration_item, rule_parameters):
        return 'NOT_APPLICABLE'
    elif is_non_compliant(configuration_item, rule_parameters):
        return 'NON_COMPLIANT'
    else:
        return 'COMPLIANT'

# USE AS IS
def is_not_applicable(configuration_item, rule_parameters):
    return configuration_item["resourceType"] not in APPLICABLE_RESOURCES

# USE AS IS
# This is the handler that's invoked by Lambda
# Most of this code is boilerplate
def lambda_handler(event, context):
    check_defined(event, 'event')
    invokingEvent = json.loads(event['invokingEvent'])
    ruleParameters = json.loads(event['ruleParameters'])
    configurationItem = get_configuration_item(invokingEvent)
    compliance = 'NOT_APPLICABLE'
    if is_applicable(configurationItem, event):
        # Invoke the compliance checking function.
        compliance = evaluate_compliance(configurationItem, ruleParameters)
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
