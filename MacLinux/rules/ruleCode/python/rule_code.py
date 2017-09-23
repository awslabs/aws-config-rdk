#
# This file made available under CC0 1.0 Universal (https://creativecommons.org/publicdomain/zero/1.0/legalcode)
#
# RULE DESCRIPTION
# This example rule checks that EC2 instances are of the desired instance type
# The desired instance type is specified in the rule parameters.
#
# RULE DETAILS
# Trigger Type (Change Triggered or Periodic: Change Triggered

# Required Parameters: desiredInstanceType - t2.micro
# Rule parameters defined in rules/ruleCode/ruleParameters.txt

import json

# This rule needs to be uploaded with rule_util.py. It is automatically done when using the RDK.
from rule_util import *

# If Changed Triggered, add Scope of Changes e.g. ["AWS::EC2::Instance"] or ["AWS::EC2::Instance","AWS::EC2::InternetGateway"]
# If Periodic, add Scope of Changes e.g. ["AWS::::Account"] 
APPLICABLE_RESOURCES = ["AWS::EC2::Instance"]

# This is where it's determined whether the resource is compliant or not.
# In this example, we simply decide that the resource is compliant if it is an instance and its type matches the type specified as the desired type.
# If the resource is not an instance, then we deem this resource to be not applicable. (If the scope of the rule is specified to include only
# instances, this rule would never have been invoked.)
def evaluate_compliance(configuration_item, rule_parameters):
    if configuration_item['resourceType'] not in APPLICABLE_RESOURCES:
        return 'NOT_APPLICABLE'
    elif rule_parameters['desiredInstanceType'] != configuration_item['configuration']['instanceType']:
        return 'NON_COMPLIANT'
    else:
        return 'COMPLIANT'

# USE AS IS
# This is the handler that's invoked by Lambda
@rule_handler
def lambda_handler(event, context):
    print(event)
    invoking_event = json.loads(event['invokingEvent'])
    configuration_item = invoking_event['configurationItem']
    rule_parameters = {}
    if 'ruleParameters' in event:
        rule_parameters = json.loads(event['ruleParameters'])
    return evaluate_compliance(configuration_item, rule_parameters)