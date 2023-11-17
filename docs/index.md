# Getting Started

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
rdk create MyRule --runtime python3.11 --resource-types AWS::EC2::Instance --input-parameters '{"desiredInstanceType":"t2.micro"}'
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

For a deeper dive on how to create RDK rules visit [Creating Rules](./rule-management/creating-rules.md).

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

For a deeper dive on how to run unit tests visit [Writing Unit Test](./writing-test-units.md).

## Running the tests

The `testing` directory contains scripts and buildspec files that I use
to run basic functionality tests across a variety of CLI environments
(currently Ubuntu Linux running Python 3.7/3.8/3.9/3.10, and Windows Server
running Python 3.10). If there is interest I can release a CloudFormation
template that could be used to build the test environment, let me know
if this is something you want!

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
- **Carlo DePaolis** - [depaolism](https://github.com/depaolism) _current maintainer_
- **Nima Fotouhi** - [nimaft](https://github.com/nimaft) - _current maintainer_

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
