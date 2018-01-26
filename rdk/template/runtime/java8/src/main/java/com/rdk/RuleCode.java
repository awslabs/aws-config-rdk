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
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.amazonaws.services.config.model.*;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.LambdaLogger;


public class RuleCode {

  public static ComplianceType evaluateCompliance(JsonNode invokingEvent, JsonNode ruleParameters, Context context) throws JsonProcessingException,
          IOException {
      LambdaLogger logger = context.getLogger();
      logger.log("Beginning Custom Config Rule Evaluation");

      /*
      YOUR CODE GOES HERE!
      */

      return ComplianceType.NON_COMPLIANT;
  }
}
