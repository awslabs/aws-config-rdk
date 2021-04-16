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
