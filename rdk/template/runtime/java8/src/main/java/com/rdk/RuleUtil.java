/*
#    Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
#
#        http://aws.amazon.com/apache2.0/
#
#    or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
*/

package com.rdk;

import java.io.IOException;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.Date;

import org.apache.commons.lang3.StringUtils;

import com.amazonaws.regions.Regions;
import com.amazonaws.services.config.AmazonConfig;
import com.amazonaws.services.config.AmazonConfigClient;
import com.amazonaws.services.config.model.*;
//import com.amazonaws.services.config.samplerules.exception.FunctionExecutionException;
import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.events.ConfigEvent;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

public class RuleUtil {

    private static final String AWS_REGION_PROPERTY = "AWS_DEFAULT_REGION";
    private static final String MESSAGE_TYPE_PROPERTY = "messageType";
    //private static final String HOST_ID = "hostId";
    //private static final String PLACEMENT = "placement";
    private static final String CONFIGURATION = "configuration";
    //private static final String IMAGE_ID = "imageId";
    private static final String STATUS_PATH = "configurationItemStatus";
    //private static final String TENANCY = "tenancy";
    private static final String RESOURCE_DELETED = "ResourceDeleted";
    private static final String RESOURCE_DELETED_NOT_RECORDED = "ResourceDeletedNotRecorded";
    private static final String CAPTURE_TIME_PATH = "configurationItemCaptureTime";
    private static final String CONFIGURATION_ITEM = "configurationItem";
    private static final String RESOURCE_ID = "resourceId";
    private static final Object RESOURCE_NOT_RECORDED = "ResourceNotRecorded";
    private static final String RESOURCE_TYPE = "resourceType";

    /**
     * This handler function is executed when AWS Lambda passes the event and context objects.
     *
     * @param event
     *            Event object published by AWS Config to invoke the function.
     * @param context
     *            Context object provided by AWS Lambda.
     * @throws IOException
     */
    public void handler(ConfigEvent event, Context context) throws IOException,Exception {
        Regions region = Regions.fromName(System.getenv(AWS_REGION_PROPERTY));
        AmazonConfig configClient = new AmazonConfigClient()
                .withRegion(region);
        doHandle(event, context, configClient);
    }

    /**
     * Handler interface used by the main handler function and test events.
     */
    public void doHandle(ConfigEvent event, Context context, AmazonConfig configClient) throws IOException,Exception {
        JsonNode ruleParameters = new ObjectMapper().readTree(event.getRuleParameters());
        JsonNode invokingEvent = new ObjectMapper().readTree(event.getInvokingEvent());
        failForIncompatibleEventTypes(invokingEvent);

        // Get Compliance result.
        ComplianceType myCompliance = ComplianceType.NOT_APPLICABLE;

        if (!isEventNotApplicable(invokingEvent, event.isEventLeftScope()))
        {
            myCompliance = RuleCode.evaluateCompliance(invokingEvent, ruleParameters, context);
        }

        // Associates the evaluation result with the AWS account published in the event.
        Evaluation evaluation = new Evaluation()
                .withComplianceResourceId(getResourceId(invokingEvent))
                .withComplianceResourceType(getResourceType(invokingEvent))
                .withOrderingTimestamp(getCiCapturedTime(invokingEvent))
                .withComplianceType(myCompliance);
        doPutEvaluations(configClient, event, evaluation);
    }

    private String getResourceType(JsonNode invokingEvent) {
        return invokingEvent.path(CONFIGURATION_ITEM).path(RESOURCE_TYPE).textValue();
    }

    private void failForIncompatibleEventTypes(JsonNode invokingEvent) throws Exception {
        String messageType = invokingEvent.path(MESSAGE_TYPE_PROPERTY).textValue();
        if (!isCompatibleMessageType(messageType)) {
            throw new Exception(String.format(
                    "Events with the message type '%s' are not evaluated for this Config rule.", messageType));
        }
    }

    private String getResourceId(JsonNode invokingEvent) {
        return invokingEvent.path(CONFIGURATION_ITEM).path(RESOURCE_ID).textValue();
    }

    private Date getCiCapturedTime(JsonNode invokingEvent) {
        return getDate(invokingEvent.path(CONFIGURATION_ITEM).path(CAPTURE_TIME_PATH).textValue());
    }

    private boolean isCompatibleMessageType(String messageType) {
        return MessageType.ConfigurationItemChangeNotification.toString().equals(messageType);
    }

    private boolean isEventNotApplicable(JsonNode invokingEvent, boolean eventLeftScope) {
        String status = invokingEvent.path(CONFIGURATION_ITEM).path(STATUS_PATH).textValue();
        return (isStatusNotApplicable(status) || eventLeftScope);
    }

    private boolean isStatusNotApplicable(String status) {
        return RESOURCE_DELETED.equals(status) || RESOURCE_DELETED_NOT_RECORDED.equals(status)
                || RESOURCE_NOT_RECORDED.equals(status);
    }

    // Sends the evaluation results to AWS Config.
    private void doPutEvaluations(AmazonConfig configClient, ConfigEvent event, Evaluation evaluation) throws Exception {
        PutEvaluationsResult result = configClient.putEvaluations(new PutEvaluationsRequest()
                .withEvaluations(evaluation)
                .withResultToken(event.getResultToken()));
        // Ends the function execution if any evaluation results are not successfully reported.
        if (result.getFailedEvaluations().size() > 0) {
            throw new Exception(String.format(
                    "The following evaluations were not successfully reported to AWS Config: %s",
                    result.getFailedEvaluations()));
        }
    }

    private Date getDate(String dateString) {
        return Date.from(Instant.from(DateTimeFormatter.ISO_INSTANT.parse(dateString)));
    }
}
