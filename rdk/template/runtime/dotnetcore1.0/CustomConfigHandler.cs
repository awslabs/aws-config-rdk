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
using System.Linq;
using System.IO;
using System.Text;

using System.Threading.Tasks;

using Amazon.Lambda.Serialization.Json;
using Amazon.Lambda.Core;

using Amazon.Lambda.ConfigEvents;
using Amazon.CloudWatchEvents;
using Amazon.ConfigService.Model;
using Amazon.ConfigService;
using Amazon.Runtime;
using Amazon.Lambda.Model;
using Newtonsoft.Json.Linq;

// Assembly attribute to enable the Lambda function's JSON input to be converted into a .NET class.
[assembly: LambdaSerializer(typeof(Amazon.Lambda.Serialization.Json.JsonSerializer))]

namespace Rdk
{
    public class CustomConfigHandler
    {
        public const String AWS_REGION_PROPERTY = "AWS_DEFAULT_REGION";
        public const String MESSAGE_TYPE_PROPERTY = "messageType";
        public const String HOST_ID = "hostId";
        public const String PLACEMENT = "placement";
        public const String CONFIGURATION = "configuration";
        public const String IMAGE_ID = "imageId";
        public const String STATUS_PATH = "configurationItemStatus";
        public const String TENANCY = "tenancy";
        public const String RESOURCE_DELETED = "ResourceDeleted";
        public const String RESOURCE_DELETED_NOT_RECORDED = "ResourceDeletedNotRecorded";
        public const String CAPTURE_TIME_PATH = "configurationItemCaptureTime";
        public const String CONFIGURATION_ITEM = "configurationItem";
        public const String RESOURCE_ID = "resourceId";
        public const String RESOURCE_NOT_RECORDED = "ResourceNotRecorded";
        public const String RESOURCE_TYPE = "resourceType";


        IAmazonConfigService ConfigService { get; set; }

        /// <summary>
        /// Default constructor. This constructor is used by Lambda to construct the instance. When invoked in a Lambda environment
        /// the AWS credentials will come from the IAM role associated with the function and the AWS region will be set to the
        /// region the Lambda function is executed in.
        /// </summary>
        public CustomConfigHandler()
        {
            Console.WriteLine("inside constructor...");
        }

        /// <summary>
        /// Constructs an instance with a preconfigured S3 client. This can be used for testing the outside of the Lambda environment.
        /// </summary>
        /// <param name="configService"></param>
        public CustomConfigHandler(IAmazonConfigService configService)
        {
            this.ConfigService = configService;
        }

        /// <summary>
        /// This method is called for every Lambda invocation. This method takes in an Config event object and can be used
        /// to respond to Config notifications.
        /// </summary>
        /// <param name="evnt"></param>
        /// <param name="context"></param>
        /// <returns>Nothing</returns>
        public async Task FunctionHandler(ConfigEvent evnt, ILambdaContext context)
        {
            Console.WriteLine("inside function handler...");
            Amazon.RegionEndpoint region = Amazon.RegionEndpoint.GetBySystemName(System.Environment.GetEnvironmentVariable(AWS_REGION_PROPERTY));
            AmazonConfigServiceClient configServiceClient = new AmazonConfigServiceClient(region);
            await DoHandle(evnt, context, configServiceClient);
        }

        private async Task DoHandle(ConfigEvent configEvent, ILambdaContext context, AmazonConfigServiceClient configServiceClient)
        {
            JObject ruleParamsObj;
            JObject configItem;

            if (configEvent.RuleParameters != null){
               ruleParamsObj = JObject.Parse(configEvent.RuleParameters.ToString());
            } else {
              ruleParamsObj = new JObject();
            }

            JObject invokingEventObj = JObject.Parse(configEvent.InvokingEvent.ToString());
            if(invokingEventObj["configurationItem"] != null){
              configItem = JObject.Parse(invokingEventObj[CONFIGURATION_ITEM].ToString());
            } else {
              configItem = new JObject();
            }

            FailForIncompatibleEventTypes(invokingEventObj);
            ComplianceType myCompliance = ComplianceType.NOT_APPLICABLE;

            if (!IsEventNotApplicable(configItem, configEvent.EventLeftScope))
            {
                myCompliance = RuleCode.EvaluateCompliance(invokingEventObj, ruleParamsObj, context);
            }

            // Associates the evaluation result with the AWS account published in the event.
            Evaluation evaluation = new Evaluation {
                ComplianceResourceId = GetResourceId(configItem),
                ComplianceResourceType = GetResourceType(configItem),
                OrderingTimestamp = GetCiCapturedTime(configItem),
                ComplianceType = myCompliance
            };

            await DoPutEvaluations(configServiceClient, configEvent, evaluation);
        }

        private String GetResourceType(JObject configItem)
        {
            return (String) configItem[RESOURCE_TYPE];
        }

        private void FailForIncompatibleEventTypes(JObject invokingEventObj)
        {
            String messageType = (String) invokingEventObj[MESSAGE_TYPE_PROPERTY];
            if (!IsCompatibleMessageType(messageType))
            {
                throw new Exception(String.Format("Events with the message type '{0}' are not evaluated for this Config rule.", messageType));
            }
        }

        private String GetResourceId(JObject configItem)
        {
            return (String) configItem[RESOURCE_ID];
        }

        private DateTime GetCiCapturedTime(JObject configItem)
        {
            return DateTime.Parse((String) configItem[CAPTURE_TIME_PATH]);
        }

        private bool IsCompatibleMessageType(String messageType)
        {
            return String.Equals(MessageType.ConfigurationItemChangeNotification.ToString(), messageType);
        }

        private bool IsEventNotApplicable(JObject configItem, bool eventLeftScope)
        {
            String status = configItem[STATUS_PATH].ToString();
            return (IsStatusNotApplicable(status) || eventLeftScope);
        }

        private bool IsStatusNotApplicable(String status)
        {
            return String.Equals(RESOURCE_DELETED, status)
                || String.Equals(RESOURCE_DELETED_NOT_RECORDED, status)
                || String.Equals(RESOURCE_NOT_RECORDED, status);
        }

        // Sends the evaluation results to AWS Config.
        private async Task DoPutEvaluations(AmazonConfigServiceClient configClient, ConfigEvent configEvent, Evaluation evaluation)
        {
            Console.WriteLine("inside DoPutEvaluations...");
            PutEvaluationsRequest req = new PutEvaluationsRequest();
            req.Evaluations.Add(evaluation);
            req.ResultToken = configEvent.ResultToken;


            Task<PutEvaluationsResponse> taskResp = configClient.PutEvaluationsAsync(req);
            PutEvaluationsResponse response = await taskResp;

            // Ends the function execution if any evaluation results are not successfully reported.
            if (response.FailedEvaluations.Count > 0) {
                throw new Exception(String.Format(
                        "The following evaluations were not successfully reported to AWS Config: %s",
                        response.FailedEvaluations));
            }
        }

        private DateTime GetDate(String dateString)
        {
            return DateTime.Parse(dateString, null, System.Globalization.DateTimeStyles.RoundtripKind);
        }

        static void Main(string[] args)
        {
            Console.WriteLine("Hello World!");
        }
    }
}
