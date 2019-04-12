# Copyright 2017-2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may
# not use this file except in compliance with the License. A copy of the License is located at
#
#        http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
# the specific language governing permissions and limitations under the License.

from rdklib import rdklib

class <%RuleName%>(rdklib.ConfigRule):
    def evaluate_compliance(event, configuration_item, valid_rule_parameters):
        """Form the evaluation(s) to be return to Config Rules

        Return either:
        None -- when no result needs to be displayed
        a string -- either COMPLIANT, NON_COMPLIANT or NOT_APPLICABLE
        a dictionary -- the evaluation dictionary, usually built by build_evaluation_from_config_item()
        a list of dictionary -- a list of evaluation dictionary , usually built by build_evaluation()

        Keyword arguments:
        event -- the event variable given in the lambda handler
        configuration_item -- the configurationItem dictionary in the invokingEvent
        valid_rule_parameters -- the output of the evaluate_parameters() representing validated parameters of the Config Rule

        Advanced Notes:
        1 -- if a resource is deleted and generate a configuration change with ResourceDeleted status, the Boilerplate code will put a NOT_APPLICABLE on this resource automatically.
        2 -- if a None or a list of dictionary is returned, the old evaluation(s) which are not returned in the new evaluation list are returned as NOT_APPLICABLE by the Boilerplate code
        3 -- if None or an empty string, list or dict is returned, the Boilerplate code will put a "shadow" evaluation to feedback that the evaluation took place properly
        """

        ###############################
        # Add your custom logic here. #
        ###############################

        return 'NOT_APPLICABLE'

    def evaluate_parameters(rule_parameters):
        """Evaluate the rule parameters dictionary validity. Raise a ValueError for invalid parameters.

        Return:
        anything suitable for the evaluate_compliance()

        Keyword arguments:
        rule_parameters -- the Key/Value dictionary of the Config Rules parameters
        """
        valid_rule_parameters = rule_parameters
        return valid_rule_parameters
