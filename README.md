## Introduction

The AWS Config Rules Development Kit helps developers set up, author and test custom Config rules. It contains scripts to enable AWS Config, create a Config rule and test it with sample ConfigurationItems.

# Summary

This branch of RDK is for the alpha-testing of RDK v1.0.

RDK v1.0 will feature several changes to make RDK more useful and maintainable in the long term. The top changes are:

- Support for CfnGuard Rules
- Changing back-end deployment methodology from CloudFormation to CDK
- Refactoring the monolithic `rdk.py` file into individual files for each RDK command.

Because these changes have the potential to be breaking changes, this will initially be released using a non-semantic version (eg. alpha-1.0.0) so that existing RDK pipelines are not impacted.

# CDK Overview

RDK v1.0 uses CDK to create the CloudFormation stacks that were previously created using raw CloudFormation in RDK v0.x.

A call to `rdk deploy` will invoke several CDK commands in order:

- `diff`: determine if changes are required, stopping if no changes are required
- `bootstrap`: configure the AWS environment for CDK use
- `deploy`: apply the CFT to your AWS account

These commands will be run in the context of the standard RDK CDK App directory, defined in `rdk\frameworks\cdk`. The commands are run using Python's `subprocess` module.

## Under-the-hood

What actually happens when an `rdk deploy` command is issued?

1. The `rdk` application runs, and recognizes the command as a `deploy`.

2. The `deploy` helper function creates a `RulesDeploy` object.

3. The `RulesDeploy` object sets up a CDK runner to `diff/bootstrap/synth/deploy` the CDK template.

# Developer Instructions

These steps are used for developers who want to make and test changes to the RDK source code and compile an RDK executable.

You can run `python -m rdk` from the root directory to run RDK from the script (will be slow to run). Example:

```bash
python -m rdk deploy --all --rules-dir .\tests\integration\rdk-cdk-rule-dir\
```

You can attach the CLI to the debugger using `python -m debugpy --listen 5678 rdk deploy --all --rules-dir .\tests\integration\rdk-cdk-rule-dir\`

CDK may attempt to run `python3`, which could cause issues on Windows systems where Python is often just named `python.exe`. Copying `python.exe` to `python3.exe` is a workaround for this issue.

## Windows venv instructions

- `virtualenv myenv`
- `myenv\Scripts\activate`

Note: if using a virtual environment on Windows, you may need to `pip install -r requirements.txt` outside of your venv as well.

## Prerequisites

Install cfn-guard: https://docs.aws.amazon.com/cfn-guard/latest/ug/setting-up-linux.html

# Activate pipenv

`pipenv shell`

# Run RDK command for testing

`rdk test`
`rdk deploy`
`rdk destroy`

## Prerequisites

RDK requires `cdk` version 2 (or higher) to be installed and available in the `PATH`.

RDK is developed in Python and requires Python v3.8 (or higher).

## Installing RDK

RDK is distributed as a Python Package (`rdk`). You can install it using `pip` or other common Python methods.

### Using `pip`

_CLI_:

```bash
pip install 'rdk>=1,<2'
```

_requirements.txt_:

```text
rdk>=1,<2
```

# TODOs

- Determine the right level of verbosity and make it easy to configure verbosity

- Keep adding more features from RDK 0.x

- Integrate README.md from RDK v0 here.

- Determine whether all rules should be deployed to a single CFN Stack or whether each rule should get its own CFN Stack. The former is probably faster to deploy, but the latter matches RDK v0.

- Validate that all the requirements, etc. are contained in the `pyproject.toml` file. The goal is to keep the project lightweight (not a lot of random configuration files) but keep a good level of functionality.

- Verify that `rdklib` and `rdk` runtimes both function correctly.

- pyproject toml should replace bandit, coverage -- use RDK 0.14.0+ as template

- remove python version/terraform

- Remove Pipfile configuration, move anything important into the poetry dev grouping
  - doc dependency group, test dependency group (eg. moto, mypy), dev dependency group (eg. pylint)
- Makefile can be replaced by poetry's poethepoet taskrunner
  - Makefiles are misused!
  - Look to eks-cluster-upgrade for example

- Review any other files that should be kept/removed, such as examples, workshops, and guidelines like minimum required permissions.
