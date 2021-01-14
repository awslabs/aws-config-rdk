import json
from rule_util import *

def evaluate_compliance(configuration_item, rule_parameters):

    ###############################
    # Add your custom logic here. #
    ###############################

    return 'NOT_APPLICABLE'

# USE AS IS
# This is the handler that's invoked by Lambda
@rule_handler
def lambda_handler(event, context):
    invoking_event = json.loads(event['invokingEvent'])

    configuration_item = None
    if 'configurationItem' in invoking_event:
        configuration_item = invoking_event['configurationItem']

    rule_parameters = {}
    if 'ruleParameters' in event:
        rule_parameters = json.loads(event['ruleParameters'])
    return evaluate_compliance(configuration_item, rule_parameters)
