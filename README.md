# Summary

This branch of RDK is for the alpha-testing of RDK v1.0.

RDK v1.0 will feature several changes to make RDK more useful and maintainable in the long term. The top changes are:
- Support for CfnGuard Rules
- Changing back-end deployment methodology from CloudFormation to CDK
- Refactoring the monolithic `rdk.py` file into individual files for each RDK command.

Because these changes have the potential to be breaking changes, this will initially be released using a non-semantic version (eg. alpha-1.0.0) so that existing RDK pipelines are not impacted.

# TODO

Add README.md from RDK v0 here.

pyproject toml should replace bandit, coverage -- use RDK 0.14.0+ as template

remove python version/terraform

Remove Pipfile configuration, move anything important into the poetry dev grouping
    doc dependency group, test dependency group (eg. moto, mypy), dev dependency group (eg. pylint)
    
Makefile can be replaced by poetry's poethepoet taskrunner 
    Makefiles are misused!
    Look to eks-cluster-upgrade for example


# Developer Instructions

These steps are used for developers who want to make and test changes to the RDK source code and compile an RDK executable.

You can also run `python -m rdk` from the root directory to run RDK from the script (will be slow to run).

You can attach the CLI to the debugger using `python -m debugpy --listen 5678 rdk deploy`

CDK may attempt to run `python3`, which could cause issues on Windows systems where Python is often just named `python.exe`. Copying `python.exe` to `python3.exe` is a workaround for this issue.

## Windows venv instructions
- `virtualenv myenv`
- `myenv\Scripts\activate`

Note: if using a virtual environment on Windows, you may need to `pip install -r requirements.txt` outside of your venv as well.

## Prerequisites

Install cfn-guard: https://docs.aws.amazon.com/cfn-guard/latest/ug/setting-up-linux.html

## Set up your local environment
`make freeze`
`make init`

# Activate pipenv
`pipenv shell`

# Navigate to rules dir in integration test
`cd tests/integration/rdk-cdk-int-rules-dir`

# Run RDK command for testing
`rdk test`
`rdk deploy`
`rdk destroy`
