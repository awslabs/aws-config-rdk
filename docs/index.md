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
