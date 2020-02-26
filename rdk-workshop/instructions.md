# RDK Workshop 
This workshop is based on **SEC 304 - Compliance Automation. Set it up fast, then code it your way** session that was conducted in re:Inforce 2019 and re:Invent 2019. This local build will give the same environment setup as the lab account and anyone who interests can learn. 

The objective for this workshop is to show how a customer can create their own rules (Custom Config Rule) to detect violation on AWS resources and how they can remediate once the rule is violated. 

In the lab, we will create config rule to interact with only 2 AWS resources as below:
1. S3 Bucket - To verify if S3 bucket has enabled versioning or not. 
2. IAM User - To verify if a user has enabled MFA or not.

In case you're stuck with lab 2, 3 or 4. We have provided solutions which contains actual python code down below. 

# Pre-lab
Before you start performing the exercise in this lab, there are few resources that need to be provisioned.
You can deploy the required resources using CloudFormation template that is provided along with the instruction directory. 

### Objective
Setup lab environment using provided CloudFormation template. Once complete, you will have:

- Cloud9Role for Cloud9 EC2 instance
- 2 x IAM users (Alice, Bob)
- 1 x IAM Group (Quarantine)
- 3 x S3 Buckets (ConfigLog Bucket, NonCompliantBucket, CompliantBucket)

## Duration
5 minutes

## Task 1: Provision lab resources
1. Provision lab resources using "WorkshopSetup.yaml" CloudFormation template
  * Navigate to [AWS CloudFormation](https://console.aws.amazon.com/cloudformation/home?region=us-east-1)
  * Click on the "Create Stack"
  * Select "With new resources (standard)"
  * Under Specify template, select "Upload a template file"
  * Choose file "WorkshopSetup.yaml" from your local computer and click "Next"
  * Enter stack name "RDKWorkshopSetup" and click "Next"
  * Click "Next"
  * Check the box: I acknowledge that AWS CloudFormation might create IAM resources with custom names.
  * Click "Create Stack" 


# Lab 1: Launching a Security Hub Standard and a Managed Config Rule
In this lab, you will launch a Compliance Standard from AWS Security Hub. As AWS Security Hub uses Config Rules, it will require to set up Config first.

## Lab Overview

### Objectives
After completing this lab, you will be able to:

- Launch a Compliance Standard from AWS Security Hub
- Launch Managed Config Rules


### Duration
20 minutes

## Task 1: Enable AWS Config
1. Enable AWS Config with global resources (e.g. AWS IAM resources)
  * Navigate to [AWS Config](https://console.aws.amazon.com/config/home?region=us-east-1).
  * Click on the "Get Started"
  * Check the box: Include global resources (e.g., AWS IAM resources)
  * Select "Choose a bucket from your account" and choose bucket name "config-bucket-<AWS Account ID>" 
  * [if requested] Select "Use existing AWS Config service-linked role"
  * Click "Next"
  * Click "Next" again (note: we will deploy a rule later)
  * Click "Confirm"

Notes: If you get errors from AWS Config, please wait for a moment then Click "Cancel" and restart Task 1 again.

Tips: To enable AWS Config at scale, it is recommended to use AWS CloudFormation StackSets Template https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-sampletemplates.html

## Task 2: Launch a Compliance Standard from AWS Security Hub
2. Enable AWS Security Hub
  * Navigate to [AWS Security Hub](https://console.aws.amazon.com/securityhub/home?region=us-east-1).
  * Click on the "Go to Security Hub"
  * Accept the permission granted to Security Hub by clicking on "Enable AWS Security Hub"
  * You are done, the CIS Benchmark will get automatically deployed.

Note: It might take up to 2 hours to get the information about the CIS benchmark into Security Hub, we will see the result later.

## Task 3: Launch a Managed Config Rules
3. Deploy the Managed Config Rule "s3-bucket-versioning-enabled" with remediation
  * Navigate to the Config Service.
  * On the left panel, click on "Rules"
  * Click on "Add rule"
  * Type "versioning" into the "Filter by rule.." box.
  * Select "s3-bucket-versioning-enabled"
  * In the configuration of the rule, scroll down to "Choose remediation action" 
  * Select "AWS-ConfigureS3BucketVersioning" in the remediation action drop-down
  * Select "No" for Auto remediation
  * Choose "BucketName" in the Resource ID parameter drop-down
  * Leave the other options at the defaults.
  * Click "Save"

## Task 4: Remediate a Noncompliant resource
4. Visualize the results for the rule "s3-bucket-versioning-enabled"
  * Navigate to the Config Service.
  * On the left panel, click on "Rules"
  * Search for "s3-bucket-versioning-enabled" in the list of rule (scroll down if necessary).
  * Click on "s3-bucket-versioning-enabled" to see the detail of the rule.
  * Refresh the page until there is no banner ["No results available" or "Evaluating"] on the top (meaning that the rule has been executed)
  * Search for the evaluation result on a bucket named "my-bucket-to-remediate-*accountid*-*regionname*"

5. Remediate the non-compliant bucket "my-bucket-to-remediate-*accountid*-*regionname*"
  * Check the box next to the line showing **Noncompliant**
  * Click on "Remediate"
  * Refresh (with double arrow button) until completion. Note 1: the "Action executed successfully" and showing **Compliant** is not at the same time (it takes up to ~5 min), keep refreshing. Note 2: on the console, the filter of the result show the "noncompliant" by default, you will need to switch the compliance status filter to see the "compliant".

## (Optional) Going further
6. Discover all the available [Managed Config Rules](https://docs.aws.amazon.com/config/latest/developerguide/managed-rules-by-aws-config.html).

7. Navigate to [AWS System Manager Automation Documents](https://eu-west-1.console.aws.amazon.com/systems-manager/documents?region=eu-west-1) to discover all existing remediations actions.


# Lab 2: Writing Your First Config Rule
In this lab, you will create a [Custom AWS Config Rule](https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config_develop-rules.html), using the AWS Rule Development Kit. Over the subsequent labs you will update and add to this Rule as we make it more production-ready.

## Lab Overview

### Objectives
After completing this lab, you will be able to:

- Set up a development environment for RDK using Cloud9
- Write custom AWS Config Rules backed by Lambda functions.
- Test and deploy your custom Lambda functions using rdk


### Duration
40 minutes

## Task 1: Set up the Development Environment
1. Set up the Cloud9 development environment.  This lab guide is written assuming you will use Cloud9 for the sake of consistency, however if you are more comfortable working on your own laptop or dev environment skip to step 2 below.  
  * Navigate to the Cloud9 Service.
  * Click on the "Create environment" button to create a new development environment.  This will be where we create and test our new Config Rule.
  * Enter a Name and Description (Description is optional) and click "Next step".
  * Keep the default settings ("Create a new instance for environment (EC2)" and "t2.micro (1 GiB RAM + 1 vCPU)"), and make sure that the VPC and Subnet listed in Network Settings will allow access from your laptop.  Once validated, click "Next step".
  * Click "Create environment", and wait for environment setup to finish.  This may take a few minutes.
  * In Cloud9, Go to AWS Cloud9->Preferences->AWS Settings->Credentials and turn off "AWS managed temporary credentials".  This feature does not grant sufficient IAM access to set up AWS Config.
  * Keep this window open and navigate to the EC2 service: https://console.aws.amazon.com/ec2/v2/#Instances:sort=instanceId
  * Find the EC2 instance that Cloud9 spun up.  The name should match the pattern of "aws-cloud9-<environment name>-<unique ID>" where <environment name> is the Name you entered above during Cloud9 setup.
  * Set the IAM Profile of the Cloud9 instance to the "RDKCloud9InstanceProfile" role that was created by the CloudFormation stack by
    * Clicking on the checkbox next to the instance
    * In the Actions drop-down select "Instance Settings"->"Attach/Replace IAM Role"
    * Select the "RDKCloud9InstanceProfile" Role and click "Apply".
  * Return to your Cloud9 environment and continue on at step 5.
2. (Skip to step 3 if you completed step 1), in order to complete this Lab in your own development environment, make sure the following pre-requisites are met:
  * You have access to python and pip
  * You have access to a terminal and are familiar with terminal commands
  * You have access to a modern text editor or IDE such as Atom, Sublime Text, VSCode, pycharm, etc.
  * You have sufficient permissions in the AWS Account to create the necessary Config Rules, Lambda Functions, IAM Roles, and IAM Users

## Task 2: Install RDK
3. In the terminal window run the following commands:

```
sudo pip install rdk
```

```
rdk -h
```

  Set your region for the terminal CLI using the following command, substituting your region for <region>:

```
export AWS_DEFAULT_REGION=<region>
```

4. Initialize AWS Config using the RDK:

```
rdk init
```

  This will make sure AWS Config is set up in the Account and Region you are connecting to.  If You have already set up Config this will not override any existing settings.

## Task 3: Create Your Custom Rule
5. Create the MFA Enabled Rule using the RDK:

```
rdk create MFA_ENABLED_RULE --runtime python3.7 --resource-types AWS::IAM::User
```

  This will create a Rule backed by a Lambda function with that uses the python3.7 runtime and is triggered by resource changes to IAM users.  In your development environment this will create a directory named MFA_ENABLED_RULE, and populate it with Lambda boilerplate code (`MFA_ENABLED_RULE.py`), a base set of unit tests (`MFA_ENABLED_RULE_test.py`), and a metadata file that RDK uses to keep track of Rule configuration (`parameters.json`).  

6. Open up the `MFA_ENABLED_RULE.py` file.  Familiarize yourself with the overall structure, particularly the stubbed out function `evaluate_compliance`.

7. The boilerplate code below the Helper Functions heading in `MFA_ENABLED_RULE.py` should not need to be modified, it is responsible for implementing the Lambda handler, validating the event from Config, and processing the values returned by the `evaluate_compliance` method.

8. The structure of the Configuration Item that AWS Config submits to your lambda function will vary depending on what type of resource triggered the evaluation.  To see a sample CI so that you can build your evaluation logic, use the `rdk sample-ci` command:

```
rdk sample-ci AWS::IAM::User
```

  and review the output.

9. You should notice that there's nothing in the CI about MFA!  In order to get at the MFA settings we're going to need to pull the User ID from the CI, and then use the [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html) library bundled with the python3.7 Lambda runtime to get the extended information from IAM.

10. Implement the logic to determine if the User supplied in the CI is compliant with our requirement that MFA be enabled.  From the `evaluate_compliance` function you can return one of the legal compliance statuses ("COMPLIANT", "NON_COMPLIANT", "NOT_APPLICABLE") as a string and the RDK-provided boilerplate will handle the rest.  If you need a hint, a basic solution is provided below.

11. As you work on your solution, from the terminal you can use the `test-local` command to evaluate the syntax of the Rule you are working on:

```
rdk test-local MFA_ENABLED_RULE
```

  Note: you can use tab-completion on the Rule name, and RDK will ignore the trailing "/".

  In a real-world scenario you would implement unit tests specific to your implementation and business logic in the test file to ensure that your code is functioning as expected.

## Task 4: Deploy and Test Your Rule
12. Once you believe your solution is complete, push it out to your AWS environment using the `deploy` command:

```
rdk deploy MFA_ENABLED_RULE
```

  This will use CloudFormation to atomically deploy the Config Rule, Lambda Function, and any necessary Lambda Permissions to allow Config to execute your code.  

13. When the CloudFormation stack has finished deploying, go to your AWS Console and navigate to the Config Service.

14. On the left-hand navigation bar, click on "Rules".  On the Rules page, verify that the MFA_ENABLED_RULE is present.  Click on the Rule name to see the details.

15. If you don't see the two IAM Users Alice and Bob that were set up by the lab Cloudformation, click the "Re-evaluate" button near the top of the page.  This will trigger a re-evaluation of resources in the Account, and may take a minute.

16. You should now see two IAM Users that are both listed as "Noncompliant".  If you want, go to the IAM Service page and add a virtual MFA to one of the users using Google Authenticator.  Once done, you should be able to come back and (possibly after manually triggering another Rule re-evaluation) see one of the Users turn to "Compliant".


# Lab 3: Periodic Rules
In this lab, you will modify your custom AWS Config Rule to be triggered on a periodic schedule as well as an event trigger.

## Lab Overview

### Objectives
After completing this lab, you will be able to:

- Use the RDK to modify the configuration of Config Rules.
- Understand the extra steps necessary to write Periodic Config Rules.


### Duration
20 minutes

## Task 1: Modify The Rule Configuration

1. In the terminal, use the `rdk modify` command to add a "maximum frequency" which will ensure the Rule is triggered on a schedule.  The maximum frequency is limited to specific parameters by Config.

```
rdk modify MFA_ENABLED_RULE --maximum-frequency One_Hour
```

## Task 2: Modify the Rule Code

2. In your text editor, open up the MFA_ENABLED_RULE.py file.  If you do not yet have a working version of this Rule from the last lab, go ahead and copy it from the solutions section at the end of this lab guide.

3. Remember that in a Periodic invocation of the Rule the configuration_item passed in to your evaluate_compliance function will be empty so we'll need to make an API call to retrieve all of the IAM users in the account and evaluate them all using the same logic as we used in the previous exercise.

4. To make that a little easier, let's refactor what we've got to make a trigger-independent `evaluate_user(username)` function out of your existing compliance evaluation logic, which we will conditionally call if the configuration_item is present.  This will preserve our existing functionality, and should look something like the following pseudo-code:

```
  def evaluate_user(username):
    <existing logic, returning a compliance string>

  def evaluate_compliance(event, configuration_item, valid_rule_parameters):
    if configuration_item:
      return evaluate_user(configuration_item['resourceName'])
    else:
      <new logic goes here>    
```

5. For the new logic we will need a more sophisticated way of returning our compliance results.  Since we have multiple IAM Users in our Account we will need to create a list of compliance results to return (don't worry, the RDK boilerplate will handle that just fine) and populate it for each user.

6. To populate our results list, we will use a helper function included in the RDK boilerplate: `build_evaluation`.  Find the function in the boilerplate and read through the docstring to better understand how to use it. For our purposes, the `resource_id` will be the UserID, and the `resource_type` will be `AWS::IAM::User`.  You can leave `annotation` empty, or fill it in with a meaningful message.

7. Using `build_evaluation`, fill in the code for getting the list of Users from the IAM service using the boto3 library, and then loop through the list calling `evaluate_user` and passing the returned value to `build_evaluation` which you can append to your results list.  Finally, you can return the completed list from `evaluate_compliance` and the RDK boilerplate will handle the `putEvaluation()` calls for you. For a basic solution for this exercise, see the Solutions section at the end of this lab guide.

8. Continue to use `rdk test-local` and the Config console to validate your code.

## Task 3: Deploy and Validate

9. Use the RDK to deploy your Rule and validate that you are getting the expected results in the Config console.  If not, you can check the Lambda execution logs for your function using the `rdk logs` command. To continuously poll for new logs, in your terminal enter the following command:

  ```
  rdk logs -f MFA_ENABLED_RULE
  ```

## (Optional) Going further
8. Discover all the available custom Rules and RDK deployment template on Github: https://github.com/awslabs/aws-config-rules

9. Submit your Rule idea in the "issues" section of Github.

# Lab 4 (on your own time): Remediation

In this lab, you will use CloudWatch Events and a Lambda Function to remediate non-compliant resources.

## Lab Overview

### Objectives
After completing this lab, you will be able to:

- Configure CloudWatch Events to trigger a Lambda Function when the compliance state of a Config Rule changes
- Create a Lambda Function to remediate compliance issues


### Duration
20 minutes

## Task 1: Update the Rule Code

1. First, let's think about our requirements.  We can't automatically add MFA to an IAM user, so we'll need to get a little more nuanced about what "compliant" means.  One approach would be to require all IAM Users without MFA to have no access in the account.  Let's implement this by using a "Quarantine" IAM Group with a deny-all policy attached.  Non-compliant users can be added to this group to shut down their access in a non-destructive way.

2. Make sure your Config solution matches the structure in the Lab 2 solution found at the end of this guide.

3. Navigate to the Lambda service.  Click on "Create Function" and choose "Author From Scratch."  For the Name enter "MFA_ENABLED_REMEDIATION", and for Runtime choose python3.7.  For the Role drop-down select "Choose an existing role", and in the "Existing role" drop-down select the "WorkshopRemediationRole" that was created by the lab setup CloudFormation template.  Click on "Create Function" to complete the Function creation.

4. Navigate to the CloudWatch service.  Click on "Rules" in the left-hand navigation.

5. Click on "Create rule".  For Event Source choose "Event Pattern".  For Service Name choose "Config", and for Event Type choose "Config Rules Compliance Change".  Leave most of the filters to the "Any ..." settings, but change "Any rule name" to "Specific rule name(s)", and type "MFA_ENABLED_RULE" in the text box.

6. On the right-hand side of the screen, click the "Add target" button.  Select "Lambda function" in the drop-down list, and then select "MFA_ENABLED_REMEDIATION" from the Function drop-down.

7. Click on the "Configure Details" button at the bottom of the screen, and then on the next page enter "MFA_ENABLED_REMEDIATION" as the Name.  Ensure that the Enabled check-box is checked, and then click on "Create rule".

8. Go back to your MFA_ENABLED_REMEDIATION Lambda Function.  It's time to update it to secure your environment!

9. The CloudWatch Event Rule will send an Event to your Lambda function every time the MFA_ENABLED_RULE changes compliance status for any IAM user.  The event that Lambda receives will look something like this:

~~~~~
{  
   'version':'0',
   'id':'de5914ad-4dfd-ec30-21ef-945d92220e43',
   'detail-type':'Config Rules Compliance Change',
   'source':'aws.config',
   'account':'212591712841',
   'time':'2018-11-08T13:49:55Z',
   'region':'us-east-2',
   'resources':[  

   ],
   'detail':{  
      'resourceId':'AIDAJ7EHXUJYDKZNSYEF0',
      'awsRegion':'us-east-2',
      'awsAccountId':'12345678012',
      'configRuleName':'MFA_ENABLED_RULE',
      'recordVersion':'1.0',
      'configRuleARN':'arn:aws:config:us-east-2:12345678012:config-rule/config-rule-q8cnh9',
      'messageType':'ComplianceChangeNotification',
      'newEvaluationResult':{  
         'evaluationResultIdentifier':{  
            'evaluationResultQualifier':{  
               'configRuleName':'MFA_ENABLED_RULE',
               'resourceType':'AWS::IAM::User',
               'resourceId':'AIDAJ7EHXUJYDKZNSYEF0'
            },
            'orderingTimestamp':'2018-11-08T13:49:50.000Z'
         },
         'complianceType':'NON_COMPLIANT',
         'resultRecordedTime':'2018-11-08T13:49:53.763Z',
         'configRuleInvokedTime':'2018-11-08T13:49:52.669Z'
      },
      'oldEvaluationResult':{  
         'evaluationResultIdentifier':{  
            'evaluationResultQualifier':{  
               'configRuleName':'12345678012',
               'resourceType':'AWS::IAM_USER',
               'resourceId':'AIDAJ7EHXUJYDKZNSYEF0'
            },
            'orderingTimestamp':'2018-07-06T19:11:24.000Z'
         },
         'complianceType':'COMPLIANT',
         'resultRecordedTime':'2018-07-06T19:11:28.194Z',
         'configRuleInvokedTime':'2018-07-06T19:11:26.430Z'
      },
      'notificationCreationTime':'2018-11-08T13:49:55.156Z',
      'resourceType':'AWS::EC2::Instance'
   }
}
~~~~~

10. From the event Lambda receives we can pull out the new evaluation result complianceType, as well as the resourceId that was affected.

11. Update the MFA_ENABLED_REMEDIATION Lambda function to check whether or not the new complianceType is NON_COMPLIANT, and if so add the User to the "QuarantinedUsers" Group that was created by the lab CloudFormation template.  We'll get the unique ID of the user rather than Name or ARN, so we'll need to call listUsers and find the username of the non-compliant User.

12. Some other hints:
  * Make sure you add `import boto3` to the top of your python code.
  * The CloudWatch Event will contain the unique ID of the IAM User, not the Username.  You will need to call IAM ListUsers and loop through the returned list.
  * If you are using an active AWS account, consider simply logging messages to show that the function is working using the print() statement, rather than making changes to your account.

13. For a basic solution to the exercise, scroll to the end of this lab guide.

# Solutions
## Lab 2: Writing Your First Config Rule
Replace the entire evaluate_compliance function with the following:

```
def evaluate_compliance(event, configuration_item, valid_rule_parameters):
    iam_client = get_client('iam', event)

    username = configuration_item['resourceName']

    response = iam_client.list_mfa_devices(UserName=username)

    if response['MFADevices']:
        return "COMPLIANT"

    return "NON_COMPLIANT"
```

## Lab 3: Periodic Rules
A production-grade solution to this challenge would include evaluating the IsTruncated value returned from the list_users() call and potentially iterate through long lists of IAM resources, but that is left as an exercise for the reader along with exception handling. A solution that will work for Accounts with fewer than 100 IAM Users would look like:

```
def evaluate_user(username, event):
    iam_client = get_client('iam', event)
    response = iam_client.list_mfa_devices(UserName=username)
    if response["MFADevices"]:
        return "COMPLIANT"
    
    return "NON_COMPLIANT"

def evaluate_compliance(event, configuration_item, valid_rule_parameters):
    if configuration_item:
        username = configuration_item['resourceName']
        return evaluate_user(username, event)
    else:
        iam_client = get_client('iam', event)

        users_response = iam_client.list_users()

        compliance_results = []
        for user in users_response['Users']:
            compliance_type = evaluate_user(user['UserName'], event)
            compliance_results.append(
                build_evaluation(
                    user['UserId'],
                    compliance_type,
                    event,
                    "AWS::IAM::User"
              )
          )

        return compliance_results
```

## Lab 4: Remediation
The function listed here will print a message to CloudWatch logs rather than actually make changes to your account.  Un-comment the add_user_to_group() line to make the remediation function fully armed and operational!

```
import json
import boto3

def lambda_handler(event, context):
    if event["detail"]["newEvaluationResult"]["complianceType"] == "NON_COMPLIANT":
        user_id = event["detail"]["resourceId"]

        #Get username from user ID
        iam = boto3.client("iam")
        users_result = iam.list_users()
        user_name = ""
        for user in users_result["Users"]:
            if user["UserId"] == user_id:
                user_name = user["UserName"]
                break

        print("Adding user {} to quarantine.".format(user_name))
        #iam.add_user_to_group(GroupName="QuarantinedUsers", UserName=user_name)
```
