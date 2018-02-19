/*
#    Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
#
#        http://aws.amazon.com/apache2.0/
#
#    or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
*/

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
