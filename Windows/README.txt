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
 - Usage: createRule.cmd PROFILE RULE_NAME APPLICABLE_RESOURCE_TYPES
 - Example Usage: createRule.cmd myCLIprofile someEc2Rule "AWS::EC2::Instance,AWS::EC2::Subnet,AWS::EC2::VPC"
     Quotes are necessary because of commas. Quotes not necessary if only one applicable resource type
 - Creates Lambda function with custom rule code, Config Rule resource, IAM
   role for Config to invoke Lambda function, and adds permissions on Lambda
   function for Config to invoke. Script is idempotent so can be reused to
   update rule code. Author rule in rules/ruleCode/rule_code.py. Currently,
   there is an example "EC2_Instance_EBS_Optimized" rule in
   rule_code.py. Replace with your own rule code. Make sure resource types are 
   consistent between rule_code.py and createRule.cmd script parameters.
   Otherwise, your rule will return NOT_APPLICABLE. rules/ruleCode/rule_util.py 
   handles the boring parts of a rule; it should not need to be modified. 
   If your rule uses parameters, see below 'Adding Rule Parameters' section. 
   Script may output some "already exists" messages if script is run multiple times, 
   but should not be a real problem as script is idempotent.
 - Rule resources:
     Lambda function - RULE_NAME
     Config Rule     - RULE_NAME
     IAM Role        - config_lambda_basic_execution

Test 
 - Usage: test.cmd RULE_NAME
 - Tests created lambda function by invoking it with Configuration Items from
   rules/testUtil/compliantCIs and rules/testUtil/noncompliantCIs directories. Expects lambda
   function to return corresponding compliance. Currently has EC2 instance CIs
   to test for the existing "EC2_Instance_EBS_Optimized" rule. Look in rules/testUtil/exampleCIs
   to find Configuration Items for the resource that you are authoring a rule for, 
   modify the CI to represent a compliant or noncompliant resource, and copy it into 
   the compliantCIs or noncompliantCIs directory. Another option is to actually
   create the AWS resource, wait for a real Configuration Item, and copy it from
   the Config console or from your S3 bucket. If rule contains parameters, see 
   below 'Adding Rule Parameters' section. 

Adding Rule Parameters
 - If your custom rule has parameters, add them in rules/ruleCode/ruleParameters.txt
   Format rule parameters like "parameter1Key":"parameter1Value","parameter2Key":"parameter2Value"
   and keep them on a single line in the file. Access them in rules/ruleCode/rule_code.py
   with rule_parameters['parameter1Key']


