# Cross-Account Deployments

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

## Functions-Only Deployment

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

## create-rule-template command

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
