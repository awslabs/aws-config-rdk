//
// This file made available under CC0 1.0 Universal (https://creativecommons.org/publicdomain/zero/1.0/legalcode)
//
// RULE DESCRIPTION
/// This example rule checks that EC2 instances are of the desired instance type
// The desired instance type is specified in the rule parameters.
//
// RULE DETAILS
// Trigger Type (Change Triggered or Periodic: Change Triggered

// Required Parameters: desiredInstanceType - t2.micro
// Rule parameters defined in rules/ruleCode/ruleParameters.txt

'use strict';

const aws = require('aws-sdk');

const config = new aws.ConfigService();
// This rule needs to be uploaded with rule_util.py. It is automatically done when using the RDK.
const rule_util = require('./rule_util');

// This is where it's determined whether the resource is compliant or not.
// In this example, we simply decide that the resource is compliant if it is an instance and its type matches the type specified as the desired type.
// If the resource is not an EC2 instance, then we deem this resource to be not applicable. (If the scope of the rule is specified to include only
// instances, this rule would never have been invoked.)
function evaluateCompliance(configurationItem, ruleParameters) {
    if (configurationItem.resourceType !== 'AWS::EC2::Instance') {
        return 'NOT_APPLICABLE';
    } else if (ruleParameters.desiredInstanceType === configurationItem.configuration.instanceType) {
        return 'COMPLIANT';
    }
    return 'NON_COMPLIANT';
}

function rule_handler(event, context, callback) {
    console.info(event);
    const invokingEvent = JSON.parse(event.invokingEvent);
    const configItem = invokingEvent.configurationItem;
    const ruleParameters = JSON.parse(event.ruleParameters);
    callback(null, evaluateCompliance(configItem, ruleParameters));
}

exports.lambda_handler = (event, context, callback) => {
    rule_util.decorate_handler(rule_handler)(event, context, callback);
}
