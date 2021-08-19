rdk
===
Rule Development Kit 
We are greatly appreciated feedback and bug reports at rdk-maintainers&#64;amazon.com! You may also create an issue on this repo.

The RDK is designed to support a "Compliance-as-Code" workflow that is intuitive and productive.  It abstracts away much of the undifferentiated heavy lifting associated with deploying AWS Config rules backed by custom lambda functions, and provides a streamlined develop-deploy-monitor iterative process.

For complete documentation, including command reference, check out the `ReadTheDocs documentation <https://rdk.readthedocs.io/en/latest/>`_.

Getting Started
===============
Uses python 3.6/3.7/3.8 and is installed via pip.  Requires you to have an AWS account and sufficient permissions to manage the Config service, and to create S3 Buckets, Roles, and Lambda Functions.  An AWS IAM Policy Document that describes the minimum necessary permissions can be found at policy/rdk-minimum-permissions.json.

Under the hood, rdk uses boto3 to make API calls to AWS, so you can set your credentials any way that boto3 recognizes (options 3 through 8 here: http://boto3.readthedocs.io/en/latest/guide/configuration.html) or pass them in with the command-line parameters --profile, --region, --access-key-id, or --secret-access-key

If you just want to use the RDK, go ahead and install it using pip::

$ pip install rdk

Alternately, if you want to see the code and/or contribute you can clone the git repo, and then from the repo directory use pip to install the package.  Use the '-e' flag to generate symlinks so that any edits you make will be reflected when you run the installed package.

If you are going to author your Lambda functions using Java you will need to have Java 8 and gradle installed.  If you are going to author your Lambda functions in C# you will need to have the dotnet CLI and the .NET Core Runtime 1.08 installed.
::

  $ pip install -e .

To make sure the rdk is installed correctly, running the package from the command line without any arguments should display help information.

::

  $ rdk
  usage: rdk [-h] [-p PROFILE] [-k ACCESS_KEY] [-s SECRET_ACCESS_KEY]
           [-r REGION]
           <command> ...
  rdk: error: the following arguments are required: <command>, <command arguments>


Usage
=====

Configure your env
------------------
To use the RDK, it's recommended to create a directory that will be your working directory.  This should be committed to a source code repo, and ideally created as a python virtualenv.  In that directory, run the ``init`` command to set up your AWS Config environment.

::

  $ rdk init
  Running init!
  Creating Config bucket config-bucket-780784666283
  Creating IAM role config-role
  Waiting for IAM role to propagate
  Config Service is ON
  Config setup complete.
  Creating Code bucket config-rule-code-bucket-780784666283ap-southeast-1

Running ``init`` subsequent times will validate your AWS Config setup and re-create any S3 buckets or IAM resources that are needed.

- If you have config delievery bucket already present in some other AWS account then use **--config-bucket-exists-in-another-account** as argument:::

  $ rdk init --config-bucket-exists-in-another-account
- If you have AWS Organizations/ControlTower Setup in your AWS environment then additionally, use **--control-tower** as argument:::

  $ rdk init --control-tower --config-bucket-exists-in-another-account
- If bucket for custom lambda code is already present in current account then use **--skip-code-bucket-creation** argument:::

  $ rdk init --skip-code-bucket-creation

Create Rules
------------
In your working directory, use the ``create`` command to start creating a new custom rule.  You must specify the runtime for the lambda function that will back the Rule, and you can also specify a resource type (or comma-separated list of types) that the Rule will evaluate or a maximum frequency for a periodic rule.  This will add a new directory for the rule and populate it with several files, including a skeleton of your Lambda code.

::

  $ rdk create MyRule --runtime python3.8 --resource-types AWS::EC2::Instance --input-parameters '{"desiredInstanceType":"t2.micro"}'
  Running create!
  Local Rule files created.

On Windows it is necessary to escape the double-quotes when specifying input parameters, so the `--input-parameters` argument would instead look something like this::

  '{\"desiredInstanceType\":\"t2.micro\"}'

Note that you can create rules that use EITHER resource-types OR maximum-frequency, but not both.  We have found that rules that try to be both event-triggered as well as periodic wind up being very complicated and so we do not recommend it as a best practice.

Edit Rules Locally
---------------------------
Once you have created the rule, edit the python file in your rule directory (in the above example it would be ``MyRule/MyRule.py``, but may be deeper into the rule directory tree depending on your chosen Lambda runtime) to add whatever logic your Rule requires in the ``evaluate_compliance`` function.  You will have access to the CI that was sent by Config, as well as any parameters configured for the Config Rule.  Your function should return either a simple compliance status (one of ``COMPLIANT``, ``NONCOMPLIANT``, or ``NOT_APPLICABLE``), or if you're using the python or node runtimes you can return a JSON object with multiple evaluation responses that the RDK will send back to AWS Config.  An example would look like::

  for sg in response['SecurityGroups']:
        evaluations.append(
        {
                'ComplianceResourceType': 'AWS::EC2::SecurityGroup',
                'ComplianceResourceId': sg['GroupId'],
                'ComplianceType': 'COMPLIANT',
                'Annotation': 'This is an important note.',
                'OrderingTimestamp': str(datetime.datetime.now())
        })


    return evaluations

This is necessary for periodic rules that are not triggered by any CI change (which means the CI that is passed in will be null), and also for attaching annotations to your evaluation results.

If you want to see what the JSON structure of a CI looks like for creating your logic, you can use

::

$ rdk sample-ci <Resource Type>

to output a formatted JSON document.

Write and Run Unit Tests
------------------------
If you are writing Config Rules using either of the Python runtimes there will be a <rule name>_test.py file deployed along with your Lambda function skeleton.  This can be used to write unit tests according to the standard Python unittest framework (documented here: https://docs.python.org/3/library/unittest.html), which can be run using the `test-local` rdk command::

  $ rdk test-local MyTestRule
  Running local test!
  Testing MyTestRule
  Looking for tests in /Users/mborch/Code/rdk-dev/MyTestRule

  ---------------------------------------------------------------------

  Ran 0 tests in 0.000s

  OK
  <unittest.runner.TextTestResult run=0 errors=0 failures=0>

The test file includes setup for the MagicMock library that can be used to stub boto3 API calls if your rule logic will involve making API calls to gather additional information about your AWS environment.  For some tips on how to do this, check out this blog post: https://sgillies.net/2017/10/19/mock-is-magic.html

Modify Rule
-----------
If you need to change the parameters of a Config rule in your working directory you can use the ``modify`` command.  Any parameters you specify will overwrite existing values, any that you do not specify will not be changed.

::

  $ rdk modify MyRule --runtime python3.6 --maximum-frequency TwentyFour_Hours --input-parameters '{"desiredInstanceType":"t2.micro"}'
  Running modify!
  Modified Rule 'MyRule'.  Use the `deploy` command to push your changes to AWS.

Again, on Windows the input parameters would look like::

  '{\"desiredInstanceType\":\"t2.micro\"}'

It is worth noting that until you actually call the ``deploy`` command your rule only exists in your working directory, none of the Rule commands discussed thus far actually makes changes to your account.

Deploy Rule
-----------
Once you have completed your compliance validation code and set your Rule's configuration, you can deploy the Rule to your account using the ``deploy`` command.  This will zip up your code (and the other associated code files, if any) into a deployable package (or run a gradle build if you have selected the java8 runtime or run the lambda packaging step from the dotnet CLI if you have selected the dotnetcore1.0 runtime), copy that zip file to S3, and then launch or update a CloudFormation stack that defines your Config Rule, Lambda function, and the necessary permissions and IAM Roles for it to function.  Since CloudFormation does not deeply inspect Lambda code objects in S3 to construct its changeset, the ``deploy`` command will also directly update the Lambda function for any subsequent deployments to make sure code changes are propagated correctly.

::

  $ rdk deploy MyRule
  Running deploy!
  Zipping MyRule
  Uploading MyRule
  Creating CloudFormation Stack for MyRule
  Waiting for CloudFormation stack operation to complete...
  ...
  Waiting for CloudFormation stack operation to complete...
  Config deploy complete.

The exact output will vary depending on Lambda runtime.  You can use the --all flag to deploy all of the rules in your working directory.

Deploy Organization Rule
------------------------
You can also deploy the Rule to your AWS Orgnization using the ``deploy-organization`` command.
For successful evaluation of custom rules in child accounts, please make sure you do one of the following: 

1. Set ASSUME_ROLE_MODE in Lambda code to True, to get the lambda to assume the Role attached on the Config Service and confirm that the role trusts the master account where the Lambda function is going to be deployed.
2. Set ASSUME_ROLE_MODE in Lambda code to True, to get the lambda to assume a custom role and define an optional parameter with key as ExecutionRoleName and set the value to your custom role name; confirm that the role trusts the master account of the organization where the Lambda function will be deployed.

::

  $ rdk deploy-organization MyRule
  Running deploy!
  Zipping MyRule
  Uploading MyRule
  Creating CloudFormation Stack for MyRule
  Waiting for CloudFormation stack operation to complete...
  ...
  Waiting for CloudFormation stack operation to complete...
  Config deploy complete.
  
The exact output will vary depending on Lambda runtime.  You can use the --all flag to deploy all of the rules in your working directory.
This command uses 'PutOrganizationConfigRule' API for the rule deployment. If a new account joins an organization, the rule is deployed to that account. When an account leaves an organization, the rule is removed. Deployment of existing organizational AWS Config Rules will only be retried for 7 hours after an account is added to your organization if a recorder is not available. You are expected to create a recorder if one doesn't exist within 7 hours of adding an account to your organization.

View Logs For Deployed Rule
---------------------------
Once the Rule has been deployed to AWS you can get the CloudWatch logs associated with your lambda function using the ``logs`` command.

::

  $ rdk logs MyRule -n 5
  2017-11-15 22:59:33 - START RequestId: 96e7639a-ca15-11e7-95a2-b1521890638d Version: $LATEST
  2017-11-15 23:41:13 - REPORT RequestId: 68e0304f-ca1b-11e7-b735-81ebae95acda    Duration: 0.50 ms    Billed Duration: 100 ms     Memory Size: 256 MB
                            Max Memory Used: 36 MB
  2017-11-15 23:41:13 - END RequestId: 68e0304f-ca1b-11e7-b735-81ebae95acda
  2017-11-15 23:41:13 - Default RDK utility class does not yet support Scheduled Notifications.
  2017-11-15 23:41:13 - START RequestId: 68e0304f-ca1b-11e7-b735-81ebae95acda Version: $LATEST

You can use the ``-n`` and ``-f`` command line flags just like the UNIX ``tail`` command to view a larger number of log events and to continuously poll for new events.  The latter option can be useful in conjunction with manually initiating Config Evaluations for your deploy Config Rule to make sure it is behaving as expected.



Running the tests
=================

The `testing` directory contains scripts and buildspec files that I use to run basic functionality tests across a variety of CLI environemnts (currently Ubuntu linux running python 3.6/3.7/3.8, and Windows Server running python3.6).  If there is interest I can release a CloudFormation template that could be used to build the test environment, let me know if this is something you want!


Advanced Features
=================
Cross-Account Deployments
-------------------------
Features have been added to the RDK to facilitate...</command></command>
