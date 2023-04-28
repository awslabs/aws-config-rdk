
# Developer Instructions

These steps are used for developers who want to make and test changes to the RDK source code.

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
