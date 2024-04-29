# AWS RDK

[![pypibadge](https://static.pepy.tech/personalized-badge/rdk?period=total&units=international_system&left_color=black&right_color=blue&left_text=downloads)](https://pepy.tech/project/rdk)
![PyPI](https://img.shields.io/pypi/v/rdk)

AWS Config Rules Development Kit

We greatly appreciate feedback and bug reports at
<rdk-maintainers@amazon.com>! You may also create an issue on this repo.

The RDK is designed to support a "Compliance-as-Code" workflow that is
intuitive and productive. It abstracts away much of the undifferentiated
heavy lifting associated with deploying AWS Config rules backed by
custom lambda functions, and provides a streamlined
develop-deploy-monitor iterative process.

For complete documentation, including command reference, check out the
[ReadTheDocs documentation](https://aws-config-rdk.readthedocs.io/).

## Getting Started

Uses Python 3.7+ and is installed via pip. Requires you to have
an AWS account and sufficient permissions to manage the Config service,
and to create S3 Buckets, Roles, and Lambda Functions. An AWS IAM Policy
Document that describes the minimum necessary permissions can be found
at `policy/rdk-minimum-permissions.json`.

Under the hood, rdk uses boto3 to make API calls to AWS, so you can set
your credentials any way that boto3 recognizes (options 3 through 8
[here](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#guide-credentials))
or pass them in with the command-line parameters `--profile`,
`--region`, `--access-key-id`, or `--secret-access-key`

If you just want to use the RDK, go ahead and install it using pip.

```bash
pip install rdk
```

Alternately, if you want to see the code and/or contribute you can clone
the git repo, and then from the repo directory use pip to install the
package. Use the `-e` flag to generate symlinks so that any edits you
make will be reflected when you run the installed package.

If you are going to author your Lambda functions using Java you will
need to have Java 8 and gradle installed. If you are going to author
your Lambda functions in C# you will need to have the dotnet CLI and the
.NET Core Runtime 1.08 installed.

```bash
pip install -e .
```

To make sure the rdk is installed correctly, running the package from
the command line without any arguments should display help information.

```bash
rdk
usage: rdk [-h] [-p PROFILE] [-k ACCESS_KEY_ID] [-s SECRET_ACCESS_KEY]
           [-r REGION] [-f REGION_FILE] [--region-set REGION_SET]
           [-v] <command> ...
rdk: error: the following arguments are required: <command>, <command arguments>
```

## Usage

### Configure your env

To use the RDK, it's recommended to create a directory that will be
your working directory. This should be committed to a source code repo,
and ideally created as a python virtualenv. In that directory, run the
`init` command to set up your AWS Config environment.

```bash
rdk init
Running init!
Creating Config bucket config-bucket-780784666283
Creating IAM role config-role
Waiting for IAM role to propagate
Config Service is ON
Config setup complete.
Creating Code bucket config-rule-code-bucket-780784666283ap-southeast-1
```

Running `init` subsequent times will validate your AWS Config setup and
re-create any S3 buckets or IAM resources that are needed.

- If you have config delivery bucket already present in some other AWS account then use `--config-bucket-exists-in-another-account` as argument.

```bash
rdk init --config-bucket-exists-in-another-account
```

- If you have AWS Organizations/ControlTower Setup in your AWS environment then additionally, use `--control-tower` as argument.

```bash
rdk init --control-tower --config-bucket-exists-in-another-account
```

- If bucket for custom lambda code is already present in current account then use `--skip-code-bucket-creation` argument.

```bash
rdk init --skip-code-bucket-creation
```

- If you want rdk to create/update and upload the rdklib-layer for you, then use `--generate-lambda-layer` argument. In supported regions, rdk will deploy the layer using the Serverless Application Repository, otherwise it will build a local lambda layer archive and upload it for use.

```bash
rdk init --generate-lambda-layer
```

- If you want rdk to give a custom name to the lambda layer for you, then use `--custom-layer-namer` argument. The Serverless Application Repository currently cannot be used for custom lambda layers.

```bash
rdk init --generate-lambda-layer --custom-layer-name <LAYER_NAME>
```

## Create Rules

In your working directory, use the `create` command to start creating a
new custom rule. You must specify the runtime for the lambda function
that will back the Rule, and you can also specify a resource type (or
comma-separated list of types) that the Rule will evaluate or a maximum
frequency for a periodic rule. This will add a new directory for the
rule and populate it with several files, including a skeleton of your
Lambda code.

```bash
rdk create MyRule --runtime python3.12 --resource-types AWS::EC2::Instance --input-parameters '{"desiredInstanceType":"t2.micro"}'
Running create!
Local Rule files created.
```

On Windows it is necessary to escape the double-quotes when specifying
input parameters, so the `--input-parameters` argument would instead
look something like this:

`'{\"desiredInstanceType\":\"t2.micro\"}'`

As of RDK v0.17.0, you can also specify `--resource-types ALL` to include all resource types.

Note that you can create rules that use EITHER resource-types OR
maximum-frequency, but not both. We have found that rules that try to be
both event-triggered as well as periodic wind up being very complicated
and so we do not recommend it as a best practice.

### Edit Rules Locally

Once you have created the rule, edit the python file in your rule
directory (in the above example it would be `MyRule/MyRule.py`, but may
be deeper into the rule directory tree depending on your chosen Lambda
runtime) to add whatever logic your Rule requires in the
`evaluate_compliance` function. You will have access to the CI that was
sent by Config, as well as any parameters configured for the Config
Rule. Your function should return either a simple compliance status (one
of `COMPLIANT`, `NON_COMPLIANT`, or `NOT_APPLICABLE`), or if you're
using the python or node runtimes you can return a JSON object with
multiple evaluation responses that the RDK will send back to AWS Config.

An example would look like:

```python
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
```

This is necessary for periodic rules that are not triggered by any CI
change (which means the CI that is passed in will be null), and also for
attaching annotations to your evaluation results.

If you want to see what the JSON structure of a CI looks like for
creating your logic, you can use

```bash
rdk sample-ci <Resource Type>
```

to output a formatted JSON document.

### Write and Run Unit Tests

If you are writing Config Rules using either of the Python runtimes
there will be a `<rule name>_test.py` file deployed along with your
Lambda function skeleton. This can be used to write unit tests according
to the standard Python unittest framework (documented
[here](https://docs.python.org/3/library/unittest.html)), which can be
run using the `test-local` rdk command:

```bash
rdk test-local MyTestRule
Running local test!
Testing MyTestRule
Looking for tests in /Users/mborch/Code/rdk-dev/MyTestRule

---------------------------------------------------------------------

Ran 0 tests in 0.000s

OK
<unittest.runner.TextTestResult run=0 errors=0 failures=0>
```

The test file includes setup for the MagicMock library that can be used
to stub boto3 API calls if your rule logic will involve making API calls
to gather additional information about your AWS environment. For some
tips on how to do this, check out this blog post:
[Mock Is Magic](https://sgillies.net/2017/10/19/mock-is-magic.html)

### Modify Rule

If you need to change the parameters of a Config rule in your working
directory you can use the `modify` command. Any parameters you specify
will overwrite existing values, any that you do not specify will not be
changed.

```bash
rdk modify MyRule --runtime python3.12 --maximum-frequency TwentyFour_Hours --input-parameters '{"desiredInstanceType":"t2.micro"}'
Running modify!
Modified Rule 'MyRule'.  Use the `deploy` command to push your changes to AWS.
```

Again, on Windows the input parameters would look like:

`'{\"desiredInstanceType\":\"t2.micro\"}'`

It is worth noting that until you actually call the `deploy` command
your rule only exists in your working directory, none of the Rule
commands discussed thus far actually makes changes to your account.

### Deploy Rule

Once you have completed your compliance validation code and set your
Rule's configuration, you can deploy the Rule to your account using the
`deploy` command. This will zip up your code (and the other associated
code files, if any) into a deployable package (or run a gradle build if
you have selected the java8 runtime or run the Lambda packaging step
from the dotnet CLI if you have selected the dotnetcore1.0 runtime),
copy that zip file to S3, and then launch or update a CloudFormation
stack that defines your Config Rule, Lambda function, and the necessary
permissions and IAM Roles for it to function. Since CloudFormation does
not deeply inspect Lambda code objects in S3 to construct its changeset,
the `deploy` command will also directly update the Lambda function for
any subsequent deployments to make sure code changes are propagated
correctly.

```bash
rdk deploy MyRule
Running deploy!
Zipping MyRule
Uploading MyRule
Creating CloudFormation Stack for MyRule
Waiting for CloudFormation stack operation to complete...
...
Waiting for CloudFormation stack operation to complete...
Config deploy complete.
```

The exact output will vary depending on Lambda runtime. You can use the
`--all` flag to deploy all of the rules in your working directory. If
you used the `--generate-lambda-layer` flag in rdk init, use the
`--generated-lambda-layer` flag for rdk deploy.

### Deploy Organization Rule

You can also deploy the Rule to your AWS Organization using the
`deploy-organization` command. For successful evaluation of custom rules
in child accounts, please make sure you do one of the following:

1. Set ASSUME_ROLE_MODE in Lambda code to True, to get the Lambda to assume the Role attached on the Config Service and confirm that the role trusts the master account where the Lambda function is going to be deployed.
2. Set ASSUME_ROLE_MODE in Lambda code to True, to get the Lambda to assume a custom role and define an optional parameter with key as ExecutionRoleName and set the value to your custom role name; confirm that the role trusts the master account of the organization where the Lambda function will be deployed.

```bash
rdk deploy-organization MyRule
Running deploy!
Zipping MyRule
Uploading MyRule
Creating CloudFormation Stack for MyRule
Waiting for CloudFormation stack operation to complete...
...
Waiting for CloudFormation stack operation to complete...
Config deploy complete.
```

The exact output will vary depending on Lambda runtime. You can use the
`--all` flag to deploy all of the rules in your working directory. This
command uses `PutOrganizationConfigRule` API for the rule deployment. If
a new account joins an organization, the rule is deployed to that
account. When an account leaves an organization, the rule is removed.
Deployment of existing organizational AWS Config Rules will only be
retried for 7 hours after an account is added to your organization if a
recorder is not available. You are expected to create a recorder if one
doesn't exist within 7 hours of adding an account to your organization.

### View Logs For Deployed Rule

Once the Rule has been deployed to AWS you can get the CloudWatch logs
associated with your Lambda function using the `logs` command.

```bash
rdk logs MyRule -n 5
2017-11-15 22:59:33 - START RequestId: 96e7639a-ca15-11e7-95a2-b1521890638d Version: $LATEST
2017-11-15 23:41:13 - REPORT RequestId: 68e0304f-ca1b-11e7-b735-81ebae95acda    Duration: 0.50 ms    Billed Duration: 100 ms     Memory Size: 256 MB     Max Memory Used: 36 MB
2017-11-15 23:41:13 - END RequestId: 68e0304f-ca1b-11e7-b735-81ebae95acda
2017-11-15 23:41:13 - Default RDK utility class does not yet support Scheduled Notifications.
2017-11-15 23:41:13 - START RequestId: 68e0304f-ca1b-11e7-b735-81ebae95acda Version: $LATEST
```

You can use the `-n` and `-f` command line flags just like the UNIX
`tail` command to view a larger number of log events and to continuously
poll for new events. The latter option can be useful in conjunction with
manually initiating Config Evaluations for your deploy Config Rule to
make sure it is behaving as expected.

## Running the tests

The `testing` directory contains scripts and buildspec files that I use
to run basic functionality tests across a variety of CLI environments
(currently Ubuntu Linux running Python 3.7/3.8/3.9/3.10, and Windows Server
running Python 3.10). If there is interest I can release a CloudFormation
template that could be used to build the test environment, let me know
if this is something you want!

## Advanced Features

### Cross-Account Deployments

Features have been added to the RDK to facilitate the cross-account
deployment pattern that enterprise customers have standardized for
custom Config Rules. A cross-account architecture is one in which the
Lambda functions are deployed to a single central "Compliance" account
(which may be the same as a central "Security" account), and the
Config Rules are deployed to any number of "Satellite" accounts that
are used by other teams or departments. This gives the compliance team
confidence that their rule logic cannot be tampered with and makes it
much easier for them to modify rule logic without having to go through a
complex deployment process to potentially hundreds of AWS accounts. The
cross-account pattern uses two advanced RDK features:

- `--functions-only` (`-f`) deployment
- `create-rule-template` command

#### Functions-Only Deployment

By using the `-f` or `--functions-only` flag on the `deploy` command the
RDK will deploy only the necessary Lambda Functions, Lambda Execution
Role, and Lambda Permissions to the account specified by the execution
credentials. It accomplishes this by batching up all of the Lambda
function CloudFormation snippets for the selected Rule(s) into a single
dynamically generated template and deploy that CloudFormation template.
One consequence of this is that subsequent deployments that specify a
different set of rules for the same stack name will update that
CloudFormation stack, and any Rules that were included in the first
deployment but not in the second will be removed. You can use the
`--stack-name` parameter to override the default CloudFormation stack
name if you need to manage different subsets of your Lambda Functions
independently. The intended usage is to deploy the functions for all of
the Config rules in the Security/Compliance account, which can be done
simply by using `rdk deploy -f --all` from your working directory.

#### create-rule-template command

This command generates a CloudFormation template that defines the AWS
Config rules themselves, along with the Config Role, Config data bucket,
Configuration Recorder, and Delivery channel necessary for the Config
rules to work in a satellite account. You must specify the file name for
the generated template using the `--output-file` or
`-o` command line flags. The generated template takes a
single parameter of the AccountID of the central compliance account that
contains the Lambda functions that will back your custom Config Rules.
The generated template can be deployed in the desired satellite accounts
through any of the means that you can deploy any other CloudFormation
template, including the console, the CLI, as a CodePipeline task, or
using StackSets. The `create-rule-template` command takes all of the
standard arguments for selecting Rules to include in the generated
template, including lists of individual Rule names, an `--all` flag, or
using the RuleSets feature described below.

```bash
rdk create-rule-template -o remote-rule-template.json --all
Generating CloudFormation template!
CloudFormation template written to remote-rule-template.json
```

### Disable the supported resource types check

It is now possible to define a resource type that is not yet supported
by rdk. To disable the supported resource check use the optional flag
'--skip-supported-resource-check' during the create command.

```bash
rdk create MyRule --runtime python3.12 --resource-types AWS::New::ResourceType --skip-supported-resource-check
'AWS::New::ResourceType' not found in list of accepted resource types.
Skip-Supported-Resource-Check Flag set (--skip-supported-resource-check), ignoring missing resource type error.
Running create!
Local Rule files created.
```

### Custom Lambda Function Name

As of version 0.7.14, instead of defaulting the lambda function names to
`RDK-Rule-Function-<RULE_NAME>` it is possible to customize the name for
the Lambda function to any 64 characters string as per Lambda's naming
standards using the optional `--custom-lambda-name` flag while
performing `rdk create`. This opens up new features like :

1. Longer config rule name.
2. Custom lambda function naming as per personal or enterprise standards.

```bash
rdk create MyLongerRuleName --runtime python3.12 --resource-types AWS::EC2::Instance --custom-lambda-name custom-prefix-for-MyLongerRuleName
Running create!
Local Rule files created.
```

The above example would create files with config rule name as
`MyLongerRuleName` and lambda function with the name
`custom-prefix-for-MyLongerRuleName` instead of
`RDK-Rule-Function-MyLongerRuleName`

### RuleSets

New as of version 0.3.11, it is possible to add RuleSet tags to rules
that can be used to deploy and test groups of rules together. Rules can
belong to multiple RuleSets, and RuleSet membership is stored only in
the parameters.json metadata. The [deploy](docs/commands/deploy.md),
[create-rule-template](docs/commands/create-rule-template.md), and [test-local](docs/commands/test-local.md)
commands are RuleSet-aware such that a RuleSet can be passed in as the
target instead of `--all` or a specific named Rule.

A comma-delimited list of RuleSets can be added to a Rule when you
create it (using the `--rulesets` flag), as part of a `modify` command,
or using new `ruleset` subcommands to add or remove individual rules
from a RuleSet.

Running `rdk rulesets list` will display a list of the RuleSets
currently defined across all of the Rules in the working directory

```bash
rdk rulesets list
RuleSets:  AnotherRuleSet MyNewSet
```

Naming a specific RuleSet will list all of the Rules that are part of
that RuleSet.

```bash
rdk rulesets list AnotherRuleSet
Rules in AnotherRuleSet :  RSTest
```

Rules can be added to or removed from RuleSets using the `add` and
`remove` subcommands:

```bash
rdk rulesets add MyNewSet RSTest
RSTest added to RuleSet MyNewSet

rdk rulesets remove AnotherRuleSet RSTest
RSTest removed from RuleSet AnotherRuleSet
```

RuleSets are a convenient way to maintain a single repository of Config
Rules that may need to have subsets of them deployed to different
environments. For example your development environment may contain some
of the Rules that you run in Production but not all of them; RuleSets
gives you a way to identify and selectively deploy the appropriate Rules
to each environment.

### Managed Rules

The RDK is able to deploy AWS Managed Rules.

To do so, create a rule using `rdk create` and provide a valid
SourceIdentifier via the `--source-identifier` CLI option. The list of
Managed Rules can be found
[here](https://docs.aws.amazon.com/config/latest/developerguide/managed-rules-by-aws-config.html)
, and note that the Identifier can be obtained by replacing the dashes
with underscores and using all capitals (for example, the
"guardduty-enabled-centralized" rule has the SourceIdentifier
"GUARDDUTY_ENABLED_CENTRALIZED"). Just like custom Rules you will need
to specify source events and/or a maximum evaluation frequency, and also
pass in any Rule parameters. The resulting Rule directory will contain
only the parameters.json file, but using `rdk deploy` or
`rdk create-rule-template` can be used to deploy the Managed Rule like
any other Custom Rule.

### Deploying Rules Across Multiple Regions

The RDK is able to run init/deploy/undeploy across multiple regions with
a `rdk -f <region file> -t <region set>`

If no region group is specified, rdk will deploy to the `default` region
set.

To create a sample starter region group, run `rdk create-region-set` to
specify the filename, add the `-o <region set output file name>` this
will create a region set with the following tests and regions
`"default":["us-east-1","us-west-1","eu-north-1","ap-east-1"],"aws-cn-region-set":["cn-north-1","cn-northwest-1"]`

### Using RDK to Generate a Lambda Layer in a region (Python3)

By default `rdk init --generate-lambda-layer` will generate an rdklib
lambda layer while running init in whatever region it is run, to force
re-generation of the layer, run `rdk init --generate-lambda-layer` again
over a region

To use this generated lambda layer, add the flag
`--generated-lambda-layer` when running `rdk deploy`. For example:
`rdk -f regions.yaml deploy LP3_TestRule_P39_lib --generated-lambda-layer`

If you created layer with a custom name (by running
`rdk init --custom-lambda-layer`, add a similar `custom-lambda-layer`
flag when running deploy.

## Support & Feedback

This project is maintained by AWS Solution Architects and Consultants.
It is not part of an AWS service and support is provided best-effort by
the maintainers. To post feedback, submit feature ideas, or report bugs,
please use the [Issues
section](https://github.com/awslabs/aws-config-rdk/issues) of this repo.

## Contributing

email us at <rdk-maintainers@amazon.com> if you have any questions. We
are happy to help and discuss.

## Contacts

- **Benjamin Morris** - [bmorrissirromb](https://github.com/bmorrissirromb) - _current maintainer_
- **Julio Delgado Jr** - [tekdj7](https://github.com/tekdj7) - _current maintainer_

## Past Contributors

- **Michael Borchert** - _Original Python version_
- **Jonathan Rault** - _Original Design, testing, feedback_
- **Greg Kim and Chris Gutierrez** - _Initial work and CI definitions_
- **Henry Huang** - _Original CFN templates and other code_
- **Santosh Kumar** - _maintainer_
- **Jose Obando** - _maintainer_
- **Jarrett Andrulis** - [jarrettandrulis](https://github.com/jarrettandrulis) - _maintainer_
- **Sandeep Batchu** - [batchus](https://github.com/batchus) - _maintainer_
- **Mark Beacom** - [mbeacom](https://github.com/mbeacom) - _maintainer_
- **Ricky Chau** - [rickychau2780](https://github.com/rickychau2780) - _maintainer_

## License

This project is licensed under the Apache 2.0 License

## Acknowledgments

- the boto3 team makes all of this magic possible.

## Link

- to view example of rules built with the RDK: [https://github.com/awslabs/aws-config-rules/tree/master/python](https://github.com/awslabs/aws-config-rules/tree/master/python)
