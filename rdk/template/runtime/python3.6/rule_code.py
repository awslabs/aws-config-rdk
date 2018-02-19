#    Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
#
#        http://aws.amazon.com/apache2.0/
#
#    or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

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
