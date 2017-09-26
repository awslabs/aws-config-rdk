The Rules Development Kit is designed to help customers setup Config, author a
Config Rule, and test the rule. This is done using Windows Batch scripts that
must be run from the command prompt. Requires having the AWS CLI downloaded 
http://docs.aws.amazon.com/cli/latest/userguide/installing.htm
and being logged in to an AWS account on the CLI
http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html.
If some aws commands fail, try updating your AWS CLI to the latest version.

Run scripts from command prompt after navigating into either 'setup' 'rules'
or 'test' directory. If you already have Config set up (recording resources),
skip setup and go to rules to author rule. 

Setup
 - Usage: setup.cmd PROFILE
 - Where PROFILE is your CLI profile, e.g. default or other custom profile of yours 
 - Sets up config by creating Config resources necessary to create Config
   rules. Needs to be run for each region that rules are created for.
 - Config resources:
     S3 bucket name                - config-bucket-<ACCOUNT_ID>
     IAM Role                      - config-role
     Config Configuration Recorder - default
     Config Delivery Channel       - default

Rules
 - Usage: createRule.cmd PROFILE RUNTIME RULE_NAME APPLICABLE_RESOURCE_TYPES
 - Example Usage: createRule.cmd myCLIProfile nodejs someEc2Rule "AWS::EC2::Instance,AWS::EC2::Subnet,AWS::EC2::VPC"
 - Creates Config Rule and Lambda function. 
   Author rule in rules/ruleCode/{nodejs|python}/rule_code.{js|py}.
   You can ignore rule_util.{js|py} It is just boilerplate/library code for the rule.
   There is an example “DesiredInstanceType” rule already written.
   Add rule parameters in rules/ruleCode/ruleParameters.txt
 - Rule resources created by script:
     Lambda function - RULE_NAME
     Config Rule     - RULE_NAME
     IAM Role        - config_lambda_basic_execution
- The lambda function $RULE_NAME.zip needs to be in the same directory as the createRule script

At this point, you have written and created a rule that maybe works, which you need to test. 
Remember that rules evaluate against certain resources, so you need to create those
resources in your account. For example, if you are writing an EC2 rule, create an ec2
instance either through the CLI or in the AWS console. Make sure it is created in the 
same region as your rule. Now, evaluate the rule and check the logs to make sure it is behaving 
correctly

EvaluateRulesAndGetLogs
 - Usage: evaluateRuleAndGetLogs.cmd PROFILE RULE_NAME
 - Example Usage: evaluateRuleAndGetLogs.cmd myCLIProfile someEc2Rule
 - This script will call StartConfigRulesEvaluation and retrieve the CloudWatch 
   logs from your created Lambda function. Alternatively, you could do this through the console.
   This will not work if you have not created a resource that is in scope of your rule.

Test 
 - Usage: test.cmd PROFILE RULE_NAME
 - Example Usage: test.cmd myCLIProfile someEc2Rule
 - This step is completely optional, for if you want to test your rule 
   against multiple compliant/noncompliant test cases. 
   Create test cases by placing Configuration Items of “compliant” resources 
   in the test/testUtil/compliantCIs directory and “noncompliant” resources in
   test/testUtil/noncompliantCIs. The script will invoke the Lambda function 
   for these resources and report back whether the rule evaluated the expected 
   compliance for these resources.
   Create the test case CIs by modifying the example CIs in test/testUtil/exampleCIs
   or get them from the Config console.

Rule Parameter guidelines
 - If your custom rule has parameters, add them in rules/ruleCode/ruleParameters.txt
   Format rule parameters like "parameter1Key":"parameter1Value","parameter2Key":"parameter2Value"
   and keep them on a single line in the file. 
