/*
#    Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
#
#        http://aws.amazon.com/apache2.0/
#
#    or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
*/

'use strict';

const aws = require('aws-sdk');

const config = new aws.ConfigService();

function evaluateCompliance(configurationItem, ruleParameters, callback) {

    /*
    ###############################
    # Add your custom logic here. #
    ###############################
    */

    callback('NOT_APPLICABLE');
}

//Boilerplate Code - You should not need to change anything below this comment.
function rule_handler(event, context, callback) {
    //console.info(event);
    const invokingEvent = JSON.parse(event.invokingEvent);
    const configItem = invokingEvent.configurationItem;
    const ruleParameters = JSON.parse(event.ruleParameters);
    evaluateCompliance(configItem, ruleParameters, function(results){
      console.log(results);
      callback(null, results);
    });
}

// Helper function used to validate input
function checkDefined(reference, referenceName) {
    if (!reference) {
        throw new Error(`Error: ${referenceName} is not defined`);
    }
    return reference;
}

// Check whether the message is OversizedConfigurationItemChangeNotification or not
function isOverSizedChangeNotification(messageType) {
    checkDefined(messageType, 'messageType');
    return messageType === 'OversizedConfigurationItemChangeNotification';
}

// Check whether the message is a ScheduledNotification or not
function isScheduledNotification(messageType) {
  checkDefined(messageType, 'messageType');
  return messageType === 'ScheduledNotification'
}

// Get configurationItem using getResourceConfigHistory API.
function getConfiguration(resourceType, resourceId, configurationCaptureTime, callback) {
    config.getResourceConfigHistory({ resourceType, resourceId, laterTime: new Date(configurationCaptureTime), limit: 1 }, (err, data) => {
        if (err) {
            callback(err, null);
        }
        const configurationItem = data.configurationItems[0];
        callback(null, configurationItem);
    });
}

// Convert from the API model to the original invocation model
/*eslint no-param-reassign: ["error", { "props": false }]*/
function convertApiConfiguration(apiConfiguration) {
    apiConfiguration.awsAccountId = apiConfiguration.accountId;
    apiConfiguration.ARN = apiConfiguration.arn;
    apiConfiguration.configurationStateMd5Hash = apiConfiguration.configurationItemMD5Hash;
    apiConfiguration.configurationItemVersion = apiConfiguration.version;
    apiConfiguration.configuration = JSON.parse(apiConfiguration.configuration);
    if ({}.hasOwnProperty.call(apiConfiguration, 'relationships')) {
        for (let i = 0; i < apiConfiguration.relationships.length; i++) {
            apiConfiguration.relationships[i].name = apiConfiguration.relationships[i].relationshipName;
        }
    }
    return apiConfiguration;
}

// Based on the type of message get the configuration item either from configurationItem in the invoking event or using the getResourceConfigHistiry API in getConfiguration function.
function getConfigurationItem(invokingEvent, callback) {
    checkDefined(invokingEvent, 'invokingEvent');
    if (isOverSizedChangeNotification(invokingEvent.messageType)) {
        const configurationItemSummary = checkDefined(invokingEvent.configurationItemSummary, 'configurationItemSummary');
        getConfiguration(configurationItemSummary.resourceType, configurationItemSummary.resourceId, configurationItemSummary.configurationItemCaptureTime, (err, apiConfigurationItem) => {
            if (err) {
                callback(err);
            }
            const configurationItem = convertApiConfiguration(apiConfigurationItem);
            callback(null, configurationItem);
        });
    } else if (isScheduledNotification(invokingEvent.messageType)) {
      callback(null, null)
    } else {
        checkDefined(invokingEvent.configurationItem, 'configurationItem');
        callback(null, invokingEvent.configurationItem);
    }
}

// Check whether the resource has been deleted. If it has, then the evaluation is unnecessary.
function isApplicable(configurationItem, event) {
    //checkDefined(configurationItem, 'configurationItem');
    checkDefined(event, 'event');
    //const status = configurationItem.configurationItemStatus;
    const eventLeftScope = event.eventLeftScope;
    //return (status === 'OK' || status === 'ResourceDiscovered') && eventLeftScope === false;
    return (eventLeftScope === false);
}

// This is the handler that's invoked by Lambda
// Most of this code is boilerplate; use as is
exports.lambda_handler = function(event, context, callback) {
    checkDefined(event, 'event');
    const invokingEvent = JSON.parse(event.invokingEvent);
    const ruleParameters = JSON.parse(event.ruleParameters);
    getConfigurationItem(invokingEvent, (err, configurationItem) => {
        if (err) {
            callback(err);
        }
        //let compliance = 'NOT_APPLICABLE';
        if (isApplicable(configurationItem, event)) {
            invokingEvent.configurationItem = configurationItem;
            event.invokingEvent = JSON.stringify(invokingEvent);
            rule_handler(event, context, (err, compliance_results) => {
                if (err) {
                    callback(err);
                }
                //compliance = computedCompliance;
                var putEvaluationsRequest = {};

                // Put together the request that reports the evaluation status
                if (typeof compliance_results === 'string' || compliance_results instanceof String){
                  putEvaluationsRequest.Evaluations = [
                      {
                          ComplianceResourceType: configurationItem.resourceType,
                          ComplianceResourceId: configurationItem.resourceId,
                          ComplianceType: compliance_results,
                          OrderingTimestamp: configurationItem.configurationItemCaptureTime
                      }
                  ];
                } else if (compliance_results instanceof Array) {
                  putEvaluationsRequest.Evaluations = [];

                  var fields = ['ComplianceResourceType', 'ComplianceResourceId', 'ComplianceType', 'OrderingTimestamp'];

                  for (var i = 0; i < compliance_results.length; i++) {
                    var missing_fields = false;
                    for (var j = 0; j < fields.length; j++) {
                      if (!compliance_results[i].hasOwnProperty(fields[j])) {
                        console.info("Missing " + fields[j] + " from custom evaluation.");
                        missing_fields = true;
                      }
                    }

                    if (!missing_fields){
                      putEvaluationsRequest.Evaluations.push(compliance_results[i]);
                    }
                  }
                } else {
                  putEvaluationsRequest.Evaluations = [
                      {
                          ComplianceResourceType: configurationItem.resourceType,
                          ComplianceResourceId: configurationItem.resourceId,
                          ComplianceType: 'INSUFFICIENT_DATA',
                          OrderingTimestamp: configurationItem.configurationItemCaptureTime
                      }
                  ];
                }

                putEvaluationsRequest.ResultToken = event.resultToken;

                // Invoke the Config API to report the result of the evaluation
                config.putEvaluations(putEvaluationsRequest, (error, data) => {
                    if (error) {
                        callback(error, null);
                    } else if (data.FailedEvaluations.length > 0) {
                        // Ends the function execution if any evaluation results are not successfully reported.
                        callback(JSON.stringify(data), null);
                    } else {
                        callback(null, data);
                    }
                });
            });
        }
    });
};
