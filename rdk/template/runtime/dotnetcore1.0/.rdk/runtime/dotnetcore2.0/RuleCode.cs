using System;
using System.Collections.Generic;
using System.Text;

using Amazon.ConfigService.Model;
using Amazon.ConfigService;
using Amazon.Lambda.Core;
using Amazon.Lambda.Model;
using Amazon.Lambda.ConfigEvents;
using Newtonsoft.Json.Linq;

namespace Rdk
{
    class RuleCode
    {
        public static ComplianceType EvaluateCompliance(JObject invokingEvent, JObject ruleParameters, ILambdaContext context)
        {
            context.Logger.LogLine("Beginning Custom Config Rule Evaluation");

            /*
            YOUR CODE GOES HERE!
            */

            return ComplianceType.NON_COMPLIANT;
        }
    }
}
