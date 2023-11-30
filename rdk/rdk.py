#    Copyright 2017-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License").
#
# You may not use this file except in compliance with the License. A copy of the License is located at
#
#        http://aws.amazon.com/apache2.0/
#
#    or in the "license" file accompanying this file.
#
#    This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#
#    See the License for the specific language governing permissions and limitations under the License.
import argparse
import base64
import fileinput
import fnmatch
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from boto3 import Session
import yaml
from builtins import input
from datetime import datetime
from os import path
import uuid
import boto3
import botocore
from botocore.exceptions import ClientError, EndpointConnectionError

# sphinx-argparse is a delight.
try:
    from rdk import MY_VERSION
except ImportError:
    MY_VERSION = "<version>"
    pass

rdk_dir = ".rdk"
rules_dir = ""
tests_dir = ""
util_filename = "rule_util"
rule_handler = "rule_code"
rule_template = "rdk-rule.template"
config_bucket_prefix = "config-bucket"
config_role_name = "config-role"
assume_role_policy_file = "configRuleAssumeRolePolicyDoc.json"
delivery_permission_policy_file = "deliveryPermissionsPolicy.json"
code_bucket_prefix = "config-rule-code-bucket-"
parameter_file_name = "parameters.json"
example_ci_dir = "example_ci"
test_ci_filename = "test_ci.json"
event_template_filename = "test_event_template.json"

rdklib_versions_filepath = os.path.join(os.path.dirname(__file__), "rdklib_versions.yaml")
RDKLIB_LAYER_VERSION = yaml.safe_load(open(rdklib_versions_filepath).read()).get("rdklib_layer_versions")

RDKLIB_LAYER_SAR_ID = "arn:aws:serverlessrepo:ap-southeast-1:711761543063:applications/rdklib"

RDKLIB_ARN_STRING = "arn:aws:lambda:{region}:711761543063:layer:rdklib-layer:{version}"
PARALLEL_COMMAND_THROTTLE_PERIOD = 2  # 2 seconds, used in running commands in parallel over multiple regions

# This need to be update whenever config service supports more resource types
# See: https://docs.aws.amazon.com/config/latest/developerguide/resource-config-reference.html
supported_resource_types_filepath = os.path.join(os.path.dirname(__file__), "supported_resource_types.yaml")
accepted_resource_types = yaml.safe_load(open(supported_resource_types_filepath).read()).get("supported_resources")

CONFIG_ROLE_ASSUME_ROLE_POLICY_DOCUMENT = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LOCAL",
            "Effect": "Allow",
            "Principal": {"Service": ["config.amazonaws.com"]},
            "Action": "sts:AssumeRole",
        },
        {
            "Sid": "REMOTE",
            "Effect": "Allow",
            "Principal": {"AWS": {"Fn::Sub": "arn:${AWS::Partition}:iam::${LambdaAccountId}:root"}},
            "Action": "sts:AssumeRole",
        },
    ],
}
CONFIG_ROLE_POLICY_DOCUMENT = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:PutObject*",
            "Resource": {"Fn::Sub": "arn:${AWS::Partition}:s3:::${ConfigBucket}/AWSLogs/${AWS::AccountId}/*"},
            "Condition": {"StringLike": {"s3:x-amz-acl": "bucket-owner-full-control"}},
        },
        {
            "Effect": "Allow",
            "Action": "s3:GetBucketAcl",
            "Resource": {"Fn::Sub": "arn:${AWS::Partition}:s3:::${ConfigBucket}"},
        },
    ],
}


def get_command_parser():
    # This is needed to get sphinx to auto-generate the CLI documentation correctly.
    if "__version__" not in globals() and "__version__" not in locals():
        __version__ = "<version>"

    parser = argparse.ArgumentParser(
        # formatter_class=argparse.RawDescriptionHelpFormatter,
        description="The RDK is a command-line utility for authoring, deploying, and testing custom AWS Config rules."
    )
    parser.add_argument("-p", "--profile", help="[optional] indicate which Profile to use.")
    parser.add_argument("-k", "--access-key-id", help="[optional] Access Key ID to use.")
    parser.add_argument("-s", "--secret-access-key", help="[optional] Secret Access Key to use.")
    parser.add_argument("-r", "--region", help="Select the region to run the command in.")
    parser.add_argument(
        "-f",
        "--region-file",
        help="[optional] File to specify which regions to run the command in parallel. Supported for init, deploy, and undeploy.",
    )
    parser.add_argument(
        "--region-set",
        help="[optional] Set of regions within the region file with which to run the command in parallel. Looks for a 'default' region set if not specified.",
    )
    # parser.add_argument('--verbose','-v', action='count')
    # Removed for now from command choices: 'test-remote', 'status'
    rdk_commands = sorted(
        [
            "clean",
            "create",
            "create-rule-template",
            "deploy",
            "deploy-organization",
            "init",
            "logs",
            "modify",
            "rulesets",
            "sample-ci",
            "test-local",
            "undeploy",
            "undeploy-organization",
            "export",
            "create-region-set",
        ]
    )

    parser.add_argument(
        "command",
        metavar="<command>",
        help=f"Command to run.  Refer to the usage instructions for each command for more details. Commands are: {rdk_commands}",
        choices=rdk_commands,
    )
    parser.add_argument(
        "command_args",
        metavar="<command arguments>",
        nargs=argparse.REMAINDER,
        help="Run `rdk <command> --help` to see command-specific arguments.",
    )
    parser.add_argument(
        "-v",
        "--version",
        help="Display the version of this tool",
        action="version",
        version="%(prog)s " + MY_VERSION,
    )

    return parser


def get_init_parser():
    parser = argparse.ArgumentParser(
        prog="rdk init",
        description="Sets up AWS Config.  This will enable configuration recording in AWS and ensure necessary S3 buckets and IAM Roles are created.",
    )

    parser.add_argument(
        "--config-bucket-exists-in-another-account",
        required=False,
        action="store_true",
        help="[optional] If the Config bucket exists in another account, remove the check of the bucket",
    )
    parser.add_argument(
        "--skip-code-bucket-creation",
        required=False,
        action="store_true",
        help='[optional] If you want to use custom code bucket for rdk, enable this and use flag --custom-code-bucket to "rdk deploy"',
    )
    parser.add_argument(
        "--control-tower",
        required=False,
        action="store_true",
        help="[optional] If your account is part of an AWS Control Tower setup --control-tower will skip the setup of configuration_recorder and delivery_channel",
    )
    parser.add_argument(
        "--generate-lambda-layer",
        required=False,
        action="store_true",
        help='[optional] Forces an update to the rdklib-layer in the region. If no rdklib-layer exists in this region then "rdk init" will automatically deploy one',
    )
    parser.add_argument(
        "--custom-layer-name",
        required=False,
        default="rdklib-layer",
        help='[optional] Sets the name of the generated lambda-layer, "rdklib-layer" by default',
    )

    return parser


def get_clean_parser():
    parser = argparse.ArgumentParser(
        prog="rdk clean",
        description="Removes AWS Config from the account.  This will disable all Config rules and no configuration changes will be recorded!",
    )
    parser.add_argument(
        "--force",
        required=False,
        action="store_true",
        help="[optional] Clean account without prompting for confirmation.",
    )

    return parser


def get_create_parser():
    return get_rule_parser(True, "create")


def get_modify_parser():
    return get_rule_parser(False, "modify")


def get_rule_parser(is_required, command):
    usage_string = "[--runtime <runtime>] [--resource-types <resource types>] [--maximum-frequency <max execution frequency>] [--input-parameters <parameter JSON>] [--tags <tags JSON>] [--rulesets <RuleSet tags>]"

    if is_required:
        usage_string = "[ --resource-types <resource types> | --maximum-frequency <max execution frequency> ] [optional configuration flags] [--runtime <runtime>] [--rulesets <RuleSet tags>]"

    parser = argparse.ArgumentParser(
        prog="rdk " + command,
        usage="rdk " + command + " <rulename> " + usage_string,
        description="Rules are stored in their own directory along with their metadata.  This command is used to "
        + command
        + " the Rule and metadata.",
    )
    parser.add_argument("rulename", metavar="<rulename>", help="Rule name to create/modify")
    parser.add_argument(
        "--description",
        help="[optional] Description of the rule",
        default="",
    )
    runtime_group = parser.add_mutually_exclusive_group()
    runtime_group.add_argument(
        "-R",
        "--runtime",
        required=False,
        help="Runtime for lambda function",
        choices=[
            "java8",
            "python3.7",
            "python3.7-lib",
            "python3.8",
            "python3.8-lib",
            "python3.9",
            "python3.9-lib",
            "python3.10",
            "python3.10-lib",
            "python3.11",
            "python3.11-lib",
        ],
        metavar="",
    )
    runtime_group.add_argument(
        "--source-identifier",
        required=False,
        help="[optional] Used only for creating Managed Rules.",
    )
    parser.add_argument(
        "-l",
        "--custom-lambda-name",
        required=False,
        help="[optional] Provide custom lambda name",
    )
    parser.set_defaults(runtime="python3.11-lib")
    parser.add_argument(
        "-r",
        "--resource-types",
        required=False,
        help="[optional] Resource types that will trigger event-based Rule evaluation. You can also specify 'ALL' to scope to all resources.",
    )
    parser.add_argument(
        "-m",
        "--maximum-frequency",
        required=False,
        help="[optional] Maximum execution frequency for scheduled Rules",
        choices=[
            "One_Hour",
            "Three_Hours",
            "Six_Hours",
            "Twelve_Hours",
            "TwentyFour_Hours",
        ],
    )
    parser.add_argument(
        "-i",
        "--input-parameters",
        help="[optional] JSON for required Config parameters.",
    )
    parser.add_argument("--optional-parameters", help="[optional] JSON for optional Config parameters.")
    parser.add_argument(
        "--tags",
        help="[optional] JSON for tags to be applied to all CFN created resources.",
    )
    parser.add_argument(
        "-s",
        "--rulesets",
        required=False,
        help="[optional] comma-delimited list of RuleSet names to add this Rule to.",
    )
    parser.add_argument(
        "--remediation-action",
        required=False,
        help="[optional] SSM document for remediation.",
    )
    parser.add_argument(
        "--remediation-action-version",
        required=False,
        help="[optional] SSM document version for remediation action.",
    )
    parser.add_argument(
        "--auto-remediate",
        action="store_true",
        required=False,
        help="[optional] Set the SSM remediation to trigger automatically.",
    )
    parser.add_argument(
        "--auto-remediation-retry-attempts",
        required=False,
        help="[optional] Number of times to retry automated remediation.",
    )
    parser.add_argument(
        "--auto-remediation-retry-time",
        required=False,
        help="[optional] Duration of automated remediation retries.",
    )
    parser.add_argument(
        "--remediation-concurrent-execution-percent",
        required=False,
        help="[optional] Concurrent execution rate of the SSM document for remediation.",
    )
    parser.add_argument(
        "--remediation-error-rate-percent",
        required=False,
        help='[optional] Error rate that will mark the batch as "failed" for SSM remediation execution.',
    )
    parser.add_argument(
        "--remediation-parameters",
        required=False,
        help="[optional] JSON-formatted string of additional parameters required by the SSM document.",
    )
    parser.add_argument(
        "--automation-document",
        required=False,
        help="[optional, beta] JSON-formatted string of the SSM Automation Document.",
    )
    parser.add_argument(
        "--skip-supported-resource-check",
        required=False,
        action="store_true",
        help="[optional] Skip the check for whether the resource type is supported or not.",
    )
    parser.add_argument(
        "--excluded-accounts",
        required=False,
        help="[optional] Comma-separated list of AWS accounts to exclude from the rule. Will only be used for organizational rules.",
    )

    return parser


def get_undeploy_parser():
    return get_deployment_parser(ForceArgument=True, Command="undeploy")


def get_undeploy_organization_parser():
    return get_deployment_organization_parser(ForceArgument=True, Command="undeploy")


def get_deploy_parser():
    return get_deployment_parser()


def get_deployment_parser(ForceArgument=False, Command="deploy"):
    direction = "to"
    if Command == "undeploy":
        direction = "from"

    parser = argparse.ArgumentParser(
        prog="rdk " + Command,
        description="Used to " + Command + " the Config Rule " + direction + " the target account.",
    )
    parser.add_argument(
        "rulename",
        metavar="<rulename>",
        nargs="*",
        help="Rule name(s) to deploy.  Rule(s) will be pushed to AWS.",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="All rules in the working directory will be deployed.",
    )
    parser.add_argument("-s", "--rulesets", required=False, help="comma-delimited list of RuleSet names")
    parser.add_argument(
        "-f",
        "--functions-only",
        action="store_true",
        required=False,
        help="[optional] Only deploy Lambda functions.  Useful for cross-account deployments.",
    )
    parser.add_argument(
        "--stack-name",
        required=False,
        help='[optional] CloudFormation Stack name for use with --functions-only option.  If omitted, "RDK-Config-Rule-Functions" will be used.',
    )
    parser.add_argument(
        "--custom-code-bucket",
        required=False,
        help="[optional] Provide the custom code S3 bucket name, which is not created with rdk init, for generated cloudformation template storage.",
    )
    parser.add_argument(
        "--rdklib-layer-arn",
        required=False,
        help="[optional] Lambda Layer ARN that contains the desired rdklib.  Note that Lambda Layers are region-specific.",
    )
    parser.add_argument(
        "--lambda-role-arn",
        required=False,
        help='[optional] Assign existing iam role to lambda functions. If omitted, "rdkLambdaRole" will be created.',
    )
    parser.add_argument(
        "--lambda-role-name",
        required=False,
        help="[optional] Assign existing iam role to lambda functions. If added, will look for a lambda role in the current account with the given name",
    )
    parser.add_argument(
        "--lambda-layers",
        required=False,
        help="[optional] Comma-separated list of Lambda Layer ARNs to deploy with your Lambda function(s).",
    )
    parser.add_argument(
        "--lambda-subnets",
        required=False,
        help="[optional] Comma-separated list of Subnets to deploy your Lambda function(s). If specified, you must also specify --lambda-security-groups.",
    )
    parser.add_argument(
        "--lambda-security-groups",
        required=False,
        help="[optional] Comma-separated list of Security Groups to deploy with your Lambda function(s). If specified, you must also specify --lambda-subnets.",
    )
    parser.add_argument(
        "--lambda-timeout",
        required=False,
        default=60,
        help="[optional] Timeout (in seconds) for the lambda function",
        type=str,
    )
    parser.add_argument(
        "--boundary-policy-arn",
        required=False,
        help='[optional] Boundary Policy ARN that will be added to "rdkLambdaRole".',
    )
    parser.add_argument(
        "-g",
        "--generated-lambda-layer",
        required=False,
        action="store_true",
        help="[optional] Forces rdk deploy to use the Python lambda layer generated by rdk init --generate-lambda-layer",
    )
    parser.add_argument(
        "--custom-layer-name",
        required=False,
        default="rdklib-layer",
        help='[optional] To use with --generated-lambda-layer, forces the flag to look for a specific lambda-layer name. If omitted, "rdklib-layer" will be used',
    )

    if ForceArgument:
        parser.add_argument(
            "--force",
            required=False,
            action="store_true",
            help="[optional] Remove selected Rules from account without prompting for confirmation.",
        )
    return parser


def get_deployment_organization_parser(ForceArgument=False, Command="deploy-organization"):
    direction = "to"
    if Command == "undeploy":
        direction = "from"

    parser = argparse.ArgumentParser(
        prog="rdk " + Command,
        description="Used to " + Command + " the Config Rule " + direction + " the target Organization.",
    )
    parser.add_argument(
        "rulename",
        metavar="<rulename>",
        nargs="*",
        help="Rule name(s) to deploy.  Rule(s) will be pushed to AWS.",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="All rules in the working directory will be deployed.",
    )
    parser.add_argument("-s", "--rulesets", required=False, help="comma-delimited list of RuleSet names")
    parser.add_argument(
        "-f",
        "--functions-only",
        action="store_true",
        required=False,
        help="[optional] Only deploy Lambda functions.  Useful for cross-account deployments.",
    )
    parser.add_argument(
        "--stack-name",
        required=False,
        help='[optional] CloudFormation Stack name for use with --functions-only option.  If omitted, "RDK-Config-Rule-Functions" will be used.',
    )
    parser.add_argument(
        "--custom-code-bucket",
        required=False,
        help="[optional] Provide the custom code S3 bucket name, which is not created with rdk init, for generated cloudformation template storage.",
    )
    parser.add_argument(
        "--rdklib-layer-arn",
        required=False,
        help="[optional] Lambda Layer ARN that contains the desired rdklib.  Note that Lambda Layers are region-specific.",
    )
    parser.add_argument(
        "--lambda-role-arn",
        required=False,
        help='[optional] Assign existing iam role to lambda functions. If omitted, "rdkLambdaRole" will be created.',
    )
    parser.add_argument(
        "--lambda-role-name",
        required=False,
        help="[optional] Assign existing iam role to lambda functions. If added, will look for a lambda role in the current account with the given name",
    )
    parser.add_argument(
        "--lambda-layers",
        required=False,
        help="[optional] Comma-separated list of Lambda Layer ARNs to deploy with your Lambda function(s).",
    )
    parser.add_argument(
        "--lambda-subnets",
        required=False,
        help="[optional] Comma-separated list of Subnets to deploy your Lambda function(s). If specified, you must also specify --lambda-security-groups.",
    )
    parser.add_argument(
        "--lambda-security-groups",
        required=False,
        help="[optional] Comma-separated list of Security Groups to deploy with your Lambda function(s). If specified, you must also specify --lambda-subnets.",
    )
    parser.add_argument(
        "--lambda-timeout",
        required=False,
        default=60,
        help="[optional] Timeout (in seconds) for the lambda function",
        type=str,
    )
    parser.add_argument(
        "--boundary-policy-arn",
        required=False,
        help='[optional] Boundary Policy ARN that will be added to "rdkLambdaRole".',
    )
    parser.add_argument(
        "-g",
        "--generated-lambda-layer",
        required=False,
        action="store_true",
        help="[optional] Forces rdk deploy to use the Python lambda layer generated by rdk init --generate-lambda-layer",
    )
    parser.add_argument(
        "--custom-layer-name",
        required=False,
        default="rdklib-layer",
        help='[optional] To use with --generated-lambda-layer, forces the flag to look for a specific lambda-layer name. If omitted, "rdklib-layer" will be used',
    )
    parser.add_argument(
        "--excluded-accounts",
        required=False,
        help="[optional] Comma-separated list of account IDs to exclude from the organization rule deployment.",
    )

    if ForceArgument:
        parser.add_argument(
            "--force",
            required=False,
            action="store_true",
            help="[optional] Remove selected Rules from account without prompting for confirmation.",
        )
    return parser


def get_export_parser(ForceArgument=False, Command="export"):
    parser = argparse.ArgumentParser(
        prog="rdk " + Command,
        description="Used to " + Command + " the Config Rule to terraform file.",
    )
    parser.add_argument(
        "rulename",
        metavar="<rulename>",
        nargs="*",
        help="Rule name(s) to export to a file.",
    )
    parser.add_argument("-s", "--rulesets", required=False, help="comma-delimited list of RuleSet names")
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="All rules in the working directory will be deployed.",
    )
    parser.add_argument(
        "--lambda-layers",
        required=False,
        help="[optional] Comma-separated list of Lambda Layer ARNs to deploy with your Lambda function(s).",
    )
    parser.add_argument(
        "--lambda-subnets",
        required=False,
        help="[optional] Comma-separated list of Subnets to deploy your Lambda function(s). If specified, you must also specify --lambda-security-groups.",
    )
    parser.add_argument(
        "--lambda-security-groups",
        required=False,
        help="[optional] Comma-separated list of Security Groups to deploy with your Lambda function(s). If specified, you must also specify --lambda-subnets.",
    )
    parser.add_argument(
        "--lambda-timeout",
        required=False,
        default=60,
        help="[optional] Timeout (in seconds) for the lambda function",
        type=str,
    )
    parser.add_argument(
        "--lambda-role-arn",
        required=False,
        help="[optional] Assign existing iam role to lambda functions. If omitted, new lambda role will be created.",
    )
    parser.add_argument(
        "--lambda-role-name",
        required=False,
        help="[optional] Assign existing iam role to lambda functions. If added, will look for a lambda role in the current account with the given name",
    )
    parser.add_argument(
        "--rdklib-layer-arn",
        required=False,
        help="[optional] Lambda Layer ARN that contains the desired rdklib.  Note that Lambda Layers are region-specific.",
    )
    parser.add_argument(
        "-v",
        "--version",
        required=True,
        help="Terraform version",
        choices=["0.11", "0.12"],
    )
    parser.add_argument("-f", "--format", required=True, help="Export Format", choices=["terraform"])
    parser.add_argument(
        "-g",
        "--generated-lambda-layer",
        required=False,
        action="store_true",
        help="[optional] Forces rdk deploy to use the Python lambda layer generated by rdk init --generate-lambda-layer",
    )
    parser.add_argument(
        "--custom-layer-name",
        required=False,
        help='[optional] To use with --generated-lambda-layer, forces the flag to look for a specific lambda-layer name. If omitted, "rdklib-layer" will be used',
    )

    return parser


def get_test_parser(command):
    parser = argparse.ArgumentParser(prog="rdk " + command, description="Used to run tests on your Config Rule code.")
    parser.add_argument(
        "rulename",
        metavar="<rulename>[,<rulename>,...]",
        nargs="*",
        help="Rule name(s) to test",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Test will be run against all rules in the working directory.",
    )
    parser.add_argument("--test-ci-json", "-j", help="[optional] JSON for test CI for testing.")
    parser.add_argument("--test-ci-types", "-t", help="[optional] CI type to use for testing.")
    parser.add_argument("--verbose", "-v", action="store_true", help="[optional] Enable full log output")
    parser.add_argument(
        "-s",
        "--rulesets",
        required=False,
        help="[optional] comma-delimited list of RuleSet names",
    )
    return parser


def get_test_local_parser():
    return get_test_parser("test-local")


def get_sample_ci_parser():
    parser = argparse.ArgumentParser(
        prog="rdk sample-ci",
        description="Provides a way to see sample configuration items for most supported resource types.",
    )
    parser.add_argument(
        "ci_type",
        metavar="<resource type>",
        help='Resource name (e.g. "AWS::EC2::Instance") to display a sample CI JSON document for.',
        choices=accepted_resource_types,
    )
    return parser


def get_logs_parser():
    parser = argparse.ArgumentParser(
        prog="rdk logs",
        usage="rdk logs <rulename> [-n/--number NUMBER] [-f/--follow]",
        description="Displays CloudWatch logs for the Lambda Function for the specified Rule.",
    )
    parser.add_argument("rulename", metavar="<rulename>", help="Rule whose logs will be displayed")
    parser.add_argument(
        "-f",
        "--follow",
        action="store_true",
        help="[optional] Continuously poll Lambda logs and write to stdout.",
    )
    parser.add_argument(
        "-n",
        "--number",
        default=3,
        help="[optional] Number of previous logged events to display.",
    )
    return parser


def get_rulesets_parser():
    parser = argparse.ArgumentParser(
        prog="rdk rulesets",
        usage="rdk rulesets [list | [ [ add | remove ] <ruleset> <rulename> ]",
        description="Used to describe and manipulate RuleSet tags on Rules.",
    )
    parser.add_argument("subcommand", help="One of list, add, or remove")
    parser.add_argument("ruleset", nargs="?", help="Name of RuleSet")
    parser.add_argument("rulename", nargs="?", help="Name of Rule to be added or removed")
    return parser


def get_create_rule_template_parser():
    parser = argparse.ArgumentParser(
        prog="rdk create-rule-template",
        description="Outputs a CloudFormation template that can be used to deploy Config Rules in other AWS Accounts.",
    )
    parser.add_argument(
        "rulename",
        metavar="<rulename>",
        nargs="*",
        help="Rule name(s) to include in template.  A CloudFormation template will be created, but Rule(s) will not be pushed to AWS.",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="All rules in the working directory will be included in the generated CloudFormation template.",
    )
    parser.add_argument(
        "-s",
        "--rulesets",
        required=False,
        help="comma-delimited RuleSet names to be included in the generated template.",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        required=True,
        default="RDK-Config-Rules",
        help="filename of generated CloudFormation template",
    )
    parser.add_argument(
        "-t",
        "--tag-config-rules-script",
        required=False,
        help="filename of generated script to tag config rules with the tags in each parameter.json",
    )
    parser.add_argument(
        "--config-role-arn",
        required=False,
        help='[optional] Assign existing iam role as config role. If omitted, "config-role" will be created.',
    )
    parser.add_argument(
        "--rules-only",
        action="store_true",
        help="[optional] Generate a CloudFormation Template that only includes the Config Rules and not the Bucket, Configuration Recorder, and Delivery Channel.",
    )
    return parser


def get_create_region_set_parser():
    parser = argparse.ArgumentParser(
        prog="rdk create-region-set",
        description="Outputs a YAML region set file for multi-region deployment.",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        required=False,
        default="regions",
        help="Filename of the generated region set file",
    )
    return parser


def parse_region_file(args):
    region_set = "default"
    if args.region_set:
        region_set = args.region_set
    try:
        region_text = yaml.safe_load(open(args.region_file, "r"))
        return region_text[region_set]
    except Exception:
        raise SyntaxError(f"Error reading regions: {region_set} in file: {args.region_file}")


def run_multi_region(args):
    my_rdk = rdk(args)
    return_val = my_rdk.process_command()
    return return_val


class rdk:
    def __init__(self, args):
        self.args = args

    @staticmethod
    def get_command_parser(self):
        return get_command_parser()

    def process_command(self):
        method_to_call = getattr(self, self.args.command.replace("-", "_"))
        exit_code = method_to_call()

        return exit_code

    def init(self):
        """
        This is a test.
        """
        self.args = get_init_parser().parse_args(self.args.command_args, self.args)

        # create custom session based on whatever credentials are available to us
        my_session = self.__get_boto_session()

        print(f"[{my_session.region_name}]: Running init!")

        # Create our ConfigService client
        my_config = my_session.client("config")

        # get accountID, AWS partition (e.g. aws or aws-us-gov), region (us-east-1, us-gov-west-1)
        identity_details = self.__get_caller_identity_details(my_session)
        account_id = identity_details["account_id"]
        partition = identity_details["partition"]

        config_recorder_exists = False
        config_recorder_name = "default"
        config_role_arn = ""
        delivery_channel_exists = False

        config_bucket_exists = False
        if self.args.config_bucket_exists_in_another_account:
            print(f"[{my_session.region_name}]: Skipping Config Bucket check due to command line args")
            config_bucket_exists = True

        config_bucket_name = config_bucket_prefix + "-" + account_id

        control_tower = False
        if self.args.control_tower:
            print(
                f"[{my_session.region_name}]: This account is part of an AWS Control Tower managed organization. Playing nicely with it"
            )
            control_tower = True

        if self.args.generate_lambda_layer:
            lambda_layer_version = self.__get_existing_lambda_layer(my_session, layer_name=self.args.custom_layer_name)
            if lambda_layer_version:
                print(f"[{my_session.region_name}]: Found Version: " + lambda_layer_version)
            if self.args.generate_lambda_layer:
                print(
                    f"[{my_session.region_name}]: --generate-lambda-layer Flag received, forcing update of the Lambda Layer in {my_session.region_name}"
                )
            else:
                print(
                    f"[{my_session.region_name}]: Lambda Layer not found in {my_session.region_name}. Creating one now"
                )
            # Try to generate lambda layer with ServerlessAppRepo, manually generate if impossible
            self.__create_new_lambda_layer(my_session, layer_name=self.args.custom_layer_name)
            lambda_layer_version = self.__get_existing_lambda_layer(my_session, layer_name=self.args.custom_layer_name)

        # Check to see if the ConfigRecorder has been created.
        recorders = my_config.describe_configuration_recorders()
        if len(recorders["ConfigurationRecorders"]) > 0:
            config_recorder_exists = True
            config_recorder_name = recorders["ConfigurationRecorders"][0]["name"]
            config_role_arn = recorders["ConfigurationRecorders"][0]["roleARN"]
            print(f"[{my_session.region_name}]: Found Config Recorder: " + config_recorder_name)
            print(f"[{my_session.region_name}]: Found Config Role: " + config_role_arn)

        delivery_channels = my_config.describe_delivery_channels()
        if len(delivery_channels["DeliveryChannels"]) > 0:
            delivery_channel_exists = True
            config_bucket_name = delivery_channels["DeliveryChannels"][0]["s3BucketName"]

        my_s3 = my_session.client("s3")

        if control_tower and not config_bucket_exists:
            print(
                "Skipping Config Bucket check since this is part of a Control Tower, which automatically creates a Config bucket."
            )
        if not control_tower and not config_bucket_exists:
            # check whether bucket exists if not create config bucket
            response = my_s3.list_buckets()
            bucket_exists = False
            for bucket in response["Buckets"]:
                if bucket["Name"] == config_bucket_name:
                    print(f"[{my_session.region_name}]: Found Bucket: " + config_bucket_name)
                    config_bucket_exists = True
                    bucket_exists = True

            if not bucket_exists:
                print(f"[{my_session.region_name}]: Creating Config bucket " + config_bucket_name)
                if my_session.region_name == "us-east-1":
                    my_s3.create_bucket(Bucket=config_bucket_name)
                else:
                    my_s3.create_bucket(
                        Bucket=config_bucket_name,
                        CreateBucketConfiguration={"LocationConstraint": my_session.region_name},
                    )

        if not config_role_arn:
            # create config role
            my_iam = my_session.client("iam")
            response = my_iam.list_roles()
            role_exists = False
            for role in response["Roles"]:
                if role["RoleName"] == config_role_name:
                    role_exists = True

            if not role_exists:
                print(f"[{my_session.region_name}]: Creating IAM role config-role")
                if partition in ["aws", "aws-us-gov"]:
                    partition_url = ".com"
                elif partition == "aws-cn":
                    partition_url = ".com.cn"
                assume_role_policy_template = open(
                    os.path.join(path.dirname(__file__), "template", assume_role_policy_file),
                    "r",
                ).read()
                assume_role_policy = json.loads(assume_role_policy_template.replace("${PARTITIONURL}", partition_url))
                assume_role_policy["Statement"].append(
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": str(account_id)},
                        "Action": "sts:AssumeRole",
                    }
                )
                my_iam.create_role(
                    RoleName=config_role_name,
                    AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                    Path="/rdk/",
                )

            # attach role policy
            my_iam.attach_role_policy(
                RoleName=config_role_name,
                PolicyArn="arn:" + partition + ":iam::aws:policy/service-role/AWS_ConfigRole",
            )
            my_iam.attach_role_policy(
                RoleName=config_role_name,
                PolicyArn="arn:" + partition + ":iam::aws:policy/ReadOnlyAccess",
            )
            policy_template = open(
                os.path.join(path.dirname(__file__), "template", delivery_permission_policy_file),
                "r",
            ).read()
            delivery_permissions_policy = policy_template.replace("${ACCOUNTID}", account_id).replace(
                "${PARTITION}", partition
            )
            my_iam.put_role_policy(
                RoleName=config_role_name,
                PolicyName="ConfigDeliveryPermissions",
                PolicyDocument=delivery_permissions_policy,
            )

            # wait for changes to propagate.
            print(f"[{my_session.region_name}]: Waiting for IAM role to propagate")
            time.sleep(16)

        # create or update config recorder
        if not config_role_arn:
            config_role_arn = "arn:" + partition + ":iam::" + account_id + ":role/rdk/config-role"

        if not control_tower and not config_recorder_exists:
            my_config.put_configuration_recorder(
                ConfigurationRecorder={
                    "name": config_recorder_name,
                    "roleARN": config_role_arn,
                    "recordingGroup": {
                        "allSupported": True,
                        "includeGlobalResourceTypes": True,
                    },
                }
            )

            if not delivery_channel_exists:
                # create delivery channel
                print(f"[{my_session.region_name}]: Creating delivery channel to bucket " + config_bucket_name)
                my_config.put_delivery_channel(
                    DeliveryChannel={
                        "name": "default",
                        "s3BucketName": config_bucket_name,
                        "configSnapshotDeliveryProperties": {"deliveryFrequency": "Six_Hours"},
                    }
                )

            # start config recorder
            my_config.start_configuration_recorder(ConfigurationRecorderName=config_recorder_name)
            print(f"[{my_session.region_name}]: Config Service is ON")
        else:
            print(
                f"[{my_session.region_name}]: Skipped put_configuration_recorder, put_delivery_channel & start_configuration_recorder as this is part of a Control Tower managed Organization"
            )

        print(f"[{my_session.region_name}]: Config setup complete.")

        # create code bucket
        code_bucket_name = code_bucket_prefix + account_id + "-" + my_session.region_name
        response = my_s3.list_buckets()
        bucket_exists = False
        for bucket in response["Buckets"]:
            if bucket["Name"] == code_bucket_name:
                bucket_exists = True
                print(f"[{my_session.region_name}]: Found code bucket: " + code_bucket_name)

        if not bucket_exists:
            if self.args.skip_code_bucket_creation:
                print(f"[{my_session.region_name}]: Skipping Code Bucket creation due to command line args")
            else:
                print(f"[{my_session.region_name}]: Creating Code bucket " + code_bucket_name)

            # Consideration for us-east-1 S3 API
            if my_session.region_name == "us-east-1":
                my_s3.create_bucket(Bucket=code_bucket_name)
            else:
                my_s3.create_bucket(
                    Bucket=code_bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": my_session.region_name},
                )

        return 0

    def clean(self):
        self.args = get_clean_parser().parse_args(self.args.command_args, self.args)

        if not self.args.force:
            confirmation = False
            while not confirmation:
                my_input = input("Delete all Rules and remove Config setup?! (y/N): ")
                if my_input.lower() == "y":
                    confirmation = True
                if my_input.lower() == "n" or my_input == "":
                    sys.exit(0)

        print("Running clean!")

        # create custom session based on whatever credentials are available to us
        my_session = self.__get_boto_session()

        # Create our ConfigService client
        my_config = my_session.client("config")

        # Create an S3 client for various things.
        s3_client = my_session.client("s3")

        # Create an IAM client!  Create all the clients!
        iam_client = my_session.client("iam")
        cfn_client = my_session.client("cloudformation")

        # get accountID
        identity_details = self.__get_caller_identity_details(my_session)
        account_id = identity_details["account_id"]

        config_recorder_name = ""
        config_role_arn = ""
        delivery_channel_exists = False
        config_bucket_name = ""

        recorders = my_config.describe_configuration_recorders()
        if len(recorders["ConfigurationRecorders"]) > 0:
            config_role_arn = recorders["ConfigurationRecorders"][0]["roleARN"]
            try:
                # First delete the Config Recorder itself.  Do we need to stop it first?  Let's stop it just to be safe.
                my_config.stop_configuration_recorder(
                    ConfigurationRecorderName=recorders["ConfigurationRecorders"][0]["name"]
                )
                my_config.delete_configuration_recorder(
                    ConfigurationRecorderName=recorders["ConfigurationRecorders"][0]["name"]
                )
            except Exception as e:
                print("Error encountered removing Configuration Recorder: " + str(e))

        # Once the config recorder has been deleted there should be no dependencies on the Config Role anymore.

        try:
            response = iam_client.get_role(RoleName=config_role_name)
            try:
                role_policy_results = iam_client.list_role_policies(RoleName=config_role_name)
                for policy_name in role_policy_results["PolicyNames"]:
                    iam_client.delete_role_policy(RoleName=config_role_name, PolicyName=policy_name)

                role_policy_results = iam_client.list_attached_role_policies(RoleName=config_role_name)
                for policy in role_policy_results["AttachedPolicies"]:
                    iam_client.detach_role_policy(RoleName=config_role_name, PolicyArn=policy["PolicyArn"])

                # Once all policies are detached we should be able to delete the Role.
                iam_client.delete_role(RoleName=config_role_name)
            except Exception as e:
                print("Error encountered removing Config Role: " + str(e))
        except Exception as e2:
            print("Error encountered finding Config Role to remove: " + str(e2))

        config_bucket_names = []
        delivery_channels = my_config.describe_delivery_channels()
        if len(delivery_channels["DeliveryChannels"]) > 0:
            for delivery_channel in delivery_channels["DeliveryChannels"]:
                config_bucket_names.append(delivery_channels["DeliveryChannels"][0]["s3BucketName"])
                try:
                    my_config.delete_delivery_channel(DeliveryChannelName=delivery_channel["name"])
                except Exception as e:
                    print("Error encountered trying to delete Delivery Channel: " + str(e))

        if config_bucket_names:
            # empty and then delete the config bucket.
            for config_bucket_name in config_bucket_names:
                try:
                    config_bucket = my_session.resource("s3").Bucket(config_bucket_name)
                    config_bucket.objects.all().delete()
                    config_bucket.delete()
                except Exception as e:
                    print("Error encountered trying to delete config bucket: " + str(e))

        # Delete any of the Rules deployed the traditional way.
        self.args.all = True
        rule_names = self.__get_rule_list_for_command()
        for rule_name in rule_names:
            my_stack_name = self.__get_stack_name_from_rule_name(rule_name)
            try:
                cfn_client.delete_stack(StackName=my_stack_name)
            except Exception as e:
                print("Error encountered deleting Rule stack: " + str(e))

        # Delete the Functions stack, if one exists.
        try:
            response = cfn_client.describe_stacks(StackName="RDK-Config-Rule-Functions")
            if response["Stacks"]:
                cfn_client.delete_stack(StackName="RDK-Config-Rule-Functions")
        except ClientError as ce:
            if ce.response["Error"]["Code"] == "ValidationError":
                print("No Functions stack found.")
        except Exception as e:
            print("Error encountered deleting Functions stack: " + str(e))

        # Delete the code bucket, if one exists.
        code_bucket_name = code_bucket_prefix + account_id + "-" + my_session.region_name
        try:
            code_bucket = my_session.resource("s3").Bucket(code_bucket_name)
            code_bucket.objects.all().delete()
            code_bucket.delete()
        except ClientError as ce:
            if ce.response["Error"]["Code"] == "NoSuchBucket":
                print("No code bucket found.")
        except Exception as e:
            print("Error encountered trying to delete code bucket: " + str(e))

        # Done!
        print("Config has been removed.")

    def create(self):
        # Parse the command-line arguments relevant for creating a Config Rule.
        self.__parse_rule_args(True)

        print("Running create!")

        if not self.args.source_identifier:
            if not self.args.runtime:
                print("Runtime is required for 'create' command.")
                return 1

            extension_mapping = {
                "java8": ".java",
                "python3.7": ".py",
                "python3.7-lib": ".py",
                "python3.8": ".py",
                "python3.8-lib": ".py",
                "python3.9": ".py",
                "python3.9-lib": ".py",
                "python3.10": ".py",
                "python3.10-lib": ".py",
                "python3.11": ".py",
                "python3.11-lib": ".py",
            }
            if self.args.runtime not in extension_mapping:
                print("rdk does not support that runtime yet.")

        # if not self.args.maximum_frequency:
        #    self.args.maximum_frequency = "TwentyFour_Hours"
        #    print("Defaulting to TwentyFour_Hours Maximum Frequency.")

        # create rule directory.
        rule_path = os.path.join(os.getcwd(), rules_dir, self.args.rulename)
        if os.path.exists(rule_path):
            print("Local Rule directory already exists.")
            return 1

        try:
            os.makedirs(os.path.join(os.getcwd(), rules_dir, self.args.rulename))

            if not self.args.source_identifier:
                # copy rule template into rule directory
                if self.args.runtime == "java8":
                    self.__create_java_rule()
                else:
                    src = os.path.join(
                        path.dirname(__file__),
                        "template",
                        "runtime",
                        self.args.runtime,
                        rule_handler + extension_mapping[self.args.runtime],
                    )
                    dst = os.path.join(
                        os.getcwd(),
                        rules_dir,
                        self.args.rulename,
                        self.args.rulename + extension_mapping[self.args.runtime],
                    )
                    shutil.copyfile(src, dst)
                    f = fileinput.input(files=dst, inplace=True)
                    for line in f:
                        if self.args.runtime in [
                            "python3.7-lib",
                            "python3.8-lib",
                            "python3.9-lib",
                            "python3.10-lib",
                            "python3.11-lib",
                        ]:
                            if self.args.resource_types:
                                applicable_resource_list = ""
                                for resource_type in self.args.resource_types.split(","):
                                    applicable_resource_list += "'" + resource_type + "', "
                                print(
                                    line.replace("<%RuleName%>", self.args.rulename)
                                    .replace(
                                        "<%ApplicableResources1%>",
                                        "\nAPPLICABLE_RESOURCES = [" + applicable_resource_list[:-2] + "]\n",
                                    )
                                    .replace(
                                        "<%ApplicableResources2%>",
                                        ", APPLICABLE_RESOURCES",
                                    ),
                                    end="",
                                )
                            else:
                                print(
                                    line.replace("<%RuleName%>", self.args.rulename)
                                    .replace("<%ApplicableResources1%>", "")
                                    .replace("<%ApplicableResources2%>", ""),
                                    end="",
                                )
                        else:
                            print(line.replace("<%RuleName%>", self.args.rulename), end="")
                    f.close()

                    src = os.path.join(
                        path.dirname(__file__),
                        "template",
                        "runtime",
                        self.args.runtime,
                        "rule_test" + extension_mapping[self.args.runtime],
                    )
                    if os.path.exists(src):
                        dst = os.path.join(
                            os.getcwd(),
                            rules_dir,
                            self.args.rulename,
                            self.args.rulename + "_test" + extension_mapping[self.args.runtime],
                        )
                        shutil.copyfile(src, dst)
                        f = fileinput.input(files=dst, inplace=True)
                        for line in f:
                            print(line.replace("<%RuleName%>", self.args.rulename), end="")
                        f.close()

                    src = os.path.join(
                        path.dirname(__file__),
                        "template",
                        "runtime",
                        self.args.runtime,
                        util_filename + extension_mapping[self.args.runtime],
                    )
                    if os.path.exists(src):
                        dst = os.path.join(
                            os.getcwd(),
                            rules_dir,
                            self.args.rulename,
                            util_filename + extension_mapping[self.args.runtime],
                        )
                        shutil.copyfile(src, dst)

            # Write the parameters to a file in the rule directory.
            self.__populate_params()

            print("Local Rule files created.")
        except Exception as e:
            print("Error during create: " + str(e))
            print("Rolling back...")

            shutil.rmtree(rule_path)

            raise e
        return 0

    def modify(self):
        # Parse the command-line arguments necessary for modifying a Config Rule.
        self.__parse_rule_args(False)

        print("Running modify!")

        self.args.rulename = self.__clean_rule_name(self.args.rulename)

        # Get existing parameters
        old_params, tags = self.__get_rule_parameters(self.args.rulename)

        if not self.args.custom_lambda_name and "CustomLambdaName" in old_params:
            self.args.custom_lambda_name = old_params["CustomLambdaName"]

        if not self.args.resource_types and "SourceEvents" in old_params:
            self.args.resource_types = old_params["SourceEvents"]

        if not self.args.maximum_frequency and "SourcePeriodic" in old_params:
            self.args.maximum_frequency = old_params["SourcePeriodic"]

        if not self.args.runtime and old_params["SourceRuntime"]:
            self.args.runtime = old_params["SourceRuntime"]

        if not self.args.input_parameters and "InputParameters" in old_params:
            self.args.input_parameters = old_params["InputParameters"]

        if not self.args.optional_parameters and "OptionalParameters" in old_params:
            self.args.optional_parameters = old_params["OptionalParameters"]

        if not self.args.source_identifier and "SourceIdentifier" in old_params:
            self.args.source_identifier = old_params["SourceIdentifier"]

        if not self.args.tags and tags:
            self.args.tags = tags

        if not self.args.remediation_action and "Remediation" in old_params:
            params = old_params["Remediation"]
            self.args.auto_remediate = params.get("Automatic", "")
            execution_controls = params.get("ExecutionControls", "")
            if execution_controls:
                ssm_controls = execution_controls["SsmControls"]
                self.args.remediation_concurrent_execution_percent = ssm_controls.get(
                    "ConcurrentExecutionRatePercentage", ""
                )
                self.args.remediation_error_rate_percent = ssm_controls.get("ErrorPercentage", "")
            self.args.remediation_parameters = json.dumps(params["Parameters"]) if params.get("Parameters") else None
            self.args.auto_remediation_retry_attempts = params.get("MaximumAutomaticAttempts", "")
            self.args.auto_remediation_retry_time = params.get("RetryAttemptSeconds", "")
            self.args.remediation_action = params.get("TargetId", "")
            self.args.remediation_action_version = params.get("TargetVersion", "")

        if "RuleSets" in old_params:
            if not self.args.rulesets:
                self.args.rulesets = old_params["RuleSets"]

        # Write the parameters to a file in the rule directory.
        self.__populate_params()

        print("Modified Rule '" + self.args.rulename + "'.  Use the `deploy` command to push your changes to AWS.")

    def undeploy(self):
        self.__parse_deploy_args(ForceArgument=True)

        if not self.args.force:
            confirmation = False
            while not confirmation:
                my_input = input("Delete specified Rules and Lambda Functions from your AWS Account? (y/N): ")
                if my_input.lower() == "y":
                    confirmation = True
                if my_input.lower() == "n" or my_input == "":
                    sys.exit(0)

        # get the rule names
        rule_names = self.__get_rule_list_for_command()

        # create custom session based on whatever credentials are available to us.
        my_session = self.__get_boto_session()

        print(f"[{my_session.region_name}]: Running un-deploy!")

        # Collect a list of all of the CloudFormation templates that we delete.  We'll need it at the end to make sure everything worked.
        deleted_stacks = []

        cfn_client = my_session.client("cloudformation")

        if self.args.functions_only:
            try:
                cfn_client.delete_stack(StackName=self.args.stack_name)
                deleted_stacks.append(self.args.stack_name)
            except ClientError as ce:
                print(
                    f"[{my_session.region_name}]: Client Error encountered attempting to delete CloudFormation stack for Lambda Functions: "
                    + str(ce)
                )
            except Exception as e:
                print(
                    f"[{my_session.region_name}]: Exception encountered attempting to delete CloudFormation stack for Lambda Functions: "
                    + str(e)
                )

            return

        for rule_name in rule_names:
            try:
                cfn_client.delete_stack(StackName=self.__get_stack_name_from_rule_name(rule_name))
                deleted_stacks.append(self.__get_stack_name_from_rule_name(rule_name))
            except ClientError as ce:
                print(
                    f"[{my_session.region_name}]: Client Error encountered attempting to delete CloudFormation stack for Rule: "
                    + str(ce)
                )
            except Exception as e:
                print(
                    f"[{my_session.region_name}]: Exception encountered attempting to delete CloudFormation stack for Rule: "
                    + str(e)
                )

        print(f"[{my_session.region_name}]: Rule removal initiated. Waiting for Stack Deletion to complete.")

        for stack_name in deleted_stacks:
            self.__wait_for_cfn_stack(cfn_client, stack_name)

        print(f"[{my_session.region_name}]: Rule removal complete, but local files have been preserved.")
        print(f"[{my_session.region_name}]: To re-deploy, use the 'deploy' command.")

    def undeploy_organization(self):
        self.__parse_deploy_args(ForceArgument=True)

        if not self.args.force:
            confirmation = False
            while not confirmation:
                my_input = input("Delete specified Rules and Lambda Functions from your Organization? (y/N): ")
                if my_input.lower() == "y":
                    confirmation = True
                if my_input.lower() == "n" or my_input == "":
                    sys.exit(0)

        # get the rule names
        rule_names = self.__get_rule_list_for_command()
        my_session = self.__get_boto_session()

        print(f"[{my_session.region_name}]: Running Organization un-deploy!")

        # create custom session based on whatever credentials are available to us.

        # Collect a list of all of the CloudFormation templates that we delete.  We'll need it at the end to make sure everything worked.
        deleted_stacks = []

        cfn_client = my_session.client("cloudformation")

        if self.args.functions_only:
            try:
                cfn_client.delete_stack(StackName=self.args.stack_name)
                deleted_stacks.append(self.args.stack_name)
            except ClientError as ce:
                print(
                    f"[{my_session.region_name}]: Client Error encountered attempting to delete CloudFormation stack for Lambda Functions: "
                    + str(ce)
                )
            except Exception as e:
                print(
                    f"[{my_session.region_name}]: Exception encountered attempting to delete CloudFormation stack for Lambda Functions: "
                    + str(e)
                )

            return

        for rule_name in rule_names:
            try:
                cfn_client.delete_stack(StackName=self.__get_stack_name_from_rule_name(rule_name))
                deleted_stacks.append(self.__get_stack_name_from_rule_name(rule_name))
            except ClientError as ce:
                print(
                    f"[{my_session.region_name}]: Client Error encountered attempting to delete CloudFormation stack for Rule: "
                    + str(ce)
                )
            except Exception as e:
                print(
                    f"[{my_session.region_name}]: Exception encountered attempting to delete CloudFormation stack for Rule: "
                    + str(e)
                )

        print(f"[{my_session.region_name}]: Rule removal initiated. Waiting for Stack Deletion to complete.")

        for stack_name in deleted_stacks:
            self.__wait_for_cfn_stack(cfn_client, stack_name)

        print(f"[{my_session.region_name}]: Rule removal complete, but local files have been preserved.")
        print(f"[{my_session.region_name}]: To re-deploy, use the 'deploy-organization' command.")

    def deploy(self):
        self.__parse_deploy_args()

        # get the rule names
        rule_names = self.__get_rule_list_for_command()
        my_session = self.__get_boto_session()
        # run the deploy code
        print(f"[{my_session.region_name}]: Running deploy!")

        # create custom session based on whatever credentials are available to us

        # get accountID
        identity_details = self.__get_caller_identity_details(my_session)
        account_id = identity_details["account_id"]
        partition = identity_details["partition"]

        if self.args.custom_code_bucket:
            code_bucket_name = self.args.custom_code_bucket
        else:
            code_bucket_name = code_bucket_prefix + account_id + "-" + my_session.region_name

        # If we're only deploying the Lambda functions (and role + permissions), branch here.  Someday the "main" execution path should use the same generated CFN templates for single-account deployment.
        if self.args.functions_only:
            # Generate the template
            function_template = self.__create_function_cloudformation_template()

            # Generate CFN parameter json
            cfn_params = [
                {
                    "ParameterKey": "SourceBucket",
                    "ParameterValue": code_bucket_name,
                }
            ]

            # Write template to S3
            my_s3_client = my_session.client("s3")
            my_s3_client.put_object(
                Body=bytes(function_template.encode("utf-8")),
                Bucket=code_bucket_name,
                Key=self.args.stack_name + ".json",
            )

            # Package code and push to S3
            s3_code_objects = {}
            for rule_name in rule_names:
                rule_params, cfn_tags = self.__get_rule_parameters(rule_name)
                if "SourceIdentifier" in rule_params:
                    print(f"[{my_session.region_name}]: Skipping code packaging for Managed Rule.")
                else:
                    s3_dst = self.__upload_function_code(
                        rule_name, rule_params, account_id, my_session, code_bucket_name
                    )
                    s3_code_objects[rule_name] = s3_dst

            my_cfn = my_session.client("cloudformation")

            # Generate the template_url regardless of region using the s3 sdk
            config = my_s3_client._client_config
            config.signature_version = botocore.UNSIGNED
            template_url = boto3.client("s3", config=config).generate_presigned_url(
                "get_object",
                ExpiresIn=0,
                Params={
                    "Bucket": code_bucket_name,
                    "Key": self.args.stack_name + ".json",
                },
            )

            # Check if stack exists.  If it does, update it.  If it doesn't, create it.

            try:
                my_stack = my_cfn.describe_stacks(StackName=self.args.stack_name)

                # If we've gotten here, stack exists and we should update it.
                print(f"[{my_session.region_name}]: Updating CloudFormation Stack for Lambda functions.")
                try:
                    cfn_args = {
                        "StackName": self.args.stack_name,
                        "TemplateURL": template_url,
                        "Parameters": cfn_params,
                        "Capabilities": ["CAPABILITY_IAM"],
                    }

                    # If no tags key is specified, or if the tags dict is empty
                    if cfn_tags is not None:
                        cfn_args["Tags"] = cfn_tags

                    response = my_cfn.update_stack(**cfn_args)

                    # wait for changes to propagate.
                    self.__wait_for_cfn_stack(my_cfn, self.args.stack_name)
                except ClientError as e:
                    if e.response["Error"]["Code"] == "ValidationError":
                        if "No updates are to be performed." in str(e):
                            # No changes made to Config rule definition, so CloudFormation won't do anything.
                            print(f"[{my_session.region_name}]: No changes to Config Rule configurations.")
                        else:
                            # Something unexpected has gone wrong.  Emit an error and bail.
                            print(f"[{my_session.region_name}]: {e}")
                            return 1
                    else:
                        raise

                # Push lambda code to functions.
                for rule_name in rule_names:
                    rule_params, cfn_tags = self.__get_rule_parameters(rule_name)
                    my_lambda_arn = self.__get_lambda_arn_for_rule(
                        rule_name,
                        partition,
                        my_session.region_name,
                        account_id,
                        rule_params,
                    )
                    if "SourceIdentifier" in rule_params:
                        print(f"[{my_session.region_name}]: Skipping Lambda upload for Managed Rule.")
                        continue

                    print(f"[{my_session.region_name}]: Publishing Lambda code...")
                    my_lambda_client = my_session.client("lambda")
                    my_lambda_client.update_function_code(
                        FunctionName=my_lambda_arn,
                        S3Bucket=code_bucket_name,
                        S3Key=s3_code_objects[rule_name],
                        Publish=True,
                    )
                    print(f"[{my_session.region_name}]: Lambda code updated.")
            except ClientError:
                # If we're in the exception, the stack does not exist and we should create it.
                print(f"[{my_session.region_name}]: Creating CloudFormation Stack for Lambda Functions.")

                cfn_args = {
                    "StackName": self.args.stack_name,
                    "TemplateURL": template_url,
                    "Parameters": cfn_params,
                    "Capabilities": ["CAPABILITY_IAM"],
                }

                # If no tags key is specified, or if the tags dict is empty
                if cfn_tags is not None:
                    cfn_args["Tags"] = cfn_tags

                response = my_cfn.create_stack(**cfn_args)

                # wait for changes to propagate.
                self.__wait_for_cfn_stack(my_cfn, self.args.stack_name)

            # We're done!  Return with great success.
            sys.exit(0)

        # If we're deploying both the functions and the Config rules, run the following process:
        for rule_name in rule_names:
            rule_params, cfn_tags = self.__get_rule_parameters(rule_name)

            # create CFN Parameters common for Managed and Custom
            source_events = "NONE"
            if "SourceEvents" in rule_params:
                source_events = rule_params["SourceEvents"]

            source_periodic = "NONE"
            if "SourcePeriodic" in rule_params:
                source_periodic = rule_params["SourcePeriodic"]

            combined_input_parameters = {}
            if "InputParameters" in rule_params:
                combined_input_parameters.update(json.loads(rule_params["InputParameters"]))

            if "OptionalParameters" in rule_params:
                # Remove empty parameters
                keys_to_delete = []
                optional_parameters_json = json.loads(rule_params["OptionalParameters"])
                for key, value in optional_parameters_json.items():
                    if not value:
                        keys_to_delete.append(key)
                for key in keys_to_delete:
                    del optional_parameters_json[key]
                combined_input_parameters.update(optional_parameters_json)

            if "SourceIdentifier" in rule_params:
                print(f"[{my_session.region_name}]: Found Managed Rule.")
                # create CFN Parameters for Managed Rules

                try:
                    rule_description = rule_params["Description"]
                except KeyError:
                    rule_description = rule_name
                my_params = [
                    {
                        "ParameterKey": "RuleName",
                        "ParameterValue": rule_name,
                    },
                    {
                        "ParameterKey": "Description",
                        "ParameterValue": rule_description,
                    },
                    {
                        "ParameterKey": "SourceEvents",
                        "ParameterValue": source_events,
                    },
                    {
                        "ParameterKey": "SourcePeriodic",
                        "ParameterValue": source_periodic,
                    },
                    {
                        "ParameterKey": "SourceInputParameters",
                        "ParameterValue": json.dumps(combined_input_parameters),
                    },
                    {
                        "ParameterKey": "SourceIdentifier",
                        "ParameterValue": rule_params["SourceIdentifier"],
                    },
                ]
                my_cfn = my_session.client("cloudformation")
                if "Remediation" in rule_params:
                    print(f"[{my_session.region_name}]: Build The CFN Template with Remediation Settings")
                    cfn_body = os.path.join(
                        path.dirname(__file__),
                        "template",
                        "configManagedRuleWithRemediation.json",
                    )
                    template_body = open(cfn_body, "r").read()
                    json_body = json.loads(template_body)
                    remediation = self.__create_remediation_cloudformation_block(rule_params["Remediation"])
                    json_body["Resources"]["Remediation"] = remediation

                    if "SSMAutomation" in rule_params:
                        # Reference the SSM Automation Role Created, if IAM is created
                        print(f"[{my_session.region_name}]: Building SSM Automation Section")
                        ssm_automation = self.__create_automation_cloudformation_block(
                            rule_params["SSMAutomation"],
                            self.__get_alphanumeric_rule_name(rule_name),
                        )
                        json_body["Resources"][
                            self.__get_alphanumeric_rule_name(rule_name + "RemediationAction")
                        ] = ssm_automation
                        if "IAM" in rule_params["SSMAutomation"]:
                            print(f"[{my_session.region_name}]: Lets Build IAM Role and Policy")
                            # TODO Check For IAM Settings
                            json_body["Resources"]["Remediation"]["Properties"]["Parameters"]["AutomationAssumeRole"][
                                "StaticValue"
                            ]["Values"] = [
                                {
                                    "Fn::GetAtt": [
                                        self.__get_alphanumeric_rule_name(rule_name + "Role"),
                                        "Arn",
                                    ]
                                }
                            ]

                            (
                                ssm_iam_role,
                                ssm_iam_policy,
                            ) = self.__create_automation_iam_cloudformation_block(
                                rule_params["SSMAutomation"],
                                self.__get_alphanumeric_rule_name(rule_name),
                            )
                            json_body["Resources"][self.__get_alphanumeric_rule_name(rule_name + "Role")] = ssm_iam_role
                            json_body["Resources"][
                                self.__get_alphanumeric_rule_name(rule_name + "Policy")
                            ] = ssm_iam_policy

                            print(f"[{my_session.region_name}]: Build Supporting SSM Resources")
                            resource_depends_on = [
                                "rdkConfigRule",
                                self.__get_alphanumeric_rule_name(rule_name + "RemediationAction"),
                            ]
                            # Builds SSM Document Before Config RUle
                            json_body["Resources"]["Remediation"]["DependsOn"] = resource_depends_on
                            json_body["Resources"]["Remediation"]["Properties"]["TargetId"] = {
                                "Ref": self.__get_alphanumeric_rule_name(rule_name + "RemediationAction")
                            }

                    try:
                        my_stack_name = self.__get_stack_name_from_rule_name(rule_name)
                        my_stack = my_cfn.describe_stacks(StackName=my_stack_name)
                        # If we've gotten here, stack exists and we should update it.
                        print(f"[{my_session.region_name}]: Updating CloudFormation Stack for " + rule_name)
                        try:
                            cfn_args = {
                                "StackName": my_stack_name,
                                "TemplateBody": json.dumps(json_body, indent=2),
                                "Parameters": my_params,
                                "Capabilities": [
                                    "CAPABILITY_IAM",
                                    "CAPABILITY_NAMED_IAM",
                                ],
                            }

                            # If no tags key is specified, or if the tags dict is empty
                            if cfn_tags is not None:
                                cfn_args["Tags"] = cfn_tags

                            response = my_cfn.update_stack(**cfn_args)
                        except ClientError as e:
                            if e.response["Error"]["Code"] == "ValidationError":
                                if "No updates are to be performed." in str(e):
                                    # No changes made to Config rule definition, so CloudFormation won't do anything.
                                    print(f"[{my_session.region_name}]: No changes to Config Rule.")
                                else:
                                    # Something unexpected has gone wrong.  Emit an error and bail.
                                    print(f"[{my_session.region_name}]: {e}")
                                    return 1
                            else:
                                raise
                    except ClientError:
                        # If we're in the exception, the stack does not exist and we should create it.
                        print(f"[{my_session.region_name}]: Creating CloudFormation Stack for " + rule_name)

                        if "Remediation" in rule_params:
                            cfn_args = {
                                "StackName": my_stack_name,
                                "TemplateBody": json.dumps(json_body, indent=2),
                                "Parameters": my_params,
                                "Capabilities": [
                                    "CAPABILITY_IAM",
                                    "CAPABILITY_NAMED_IAM",
                                ],
                            }

                        else:
                            cfn_args = {
                                "StackName": my_stack_name,
                                "TemplateBody": open(cfn_body, "r").read(),
                                "Parameters": my_params,
                            }

                        if cfn_tags is not None:
                            cfn_args["Tags"] = cfn_tags

                        response = my_cfn.create_stack(**cfn_args)

                    # wait for changes to propagate.
                    self.__wait_for_cfn_stack(my_cfn, my_stack_name)
                    continue

                else:
                    # deploy config rule
                    cfn_body = os.path.join(path.dirname(__file__), "template", "configManagedRule.json")

                    try:
                        my_stack_name = self.__get_stack_name_from_rule_name(rule_name)
                        my_stack = my_cfn.describe_stacks(StackName=my_stack_name)
                        # If we've gotten here, stack exists and we should update it.
                        print(f"[{my_session.region_name}]: Updating CloudFormation Stack for " + rule_name)
                        try:
                            cfn_args = {
                                "StackName": my_stack_name,
                                "TemplateBody": open(cfn_body, "r").read(),
                                "Parameters": my_params,
                            }

                            # If no tags key is specified, or if the tags dict is empty
                            if cfn_tags is not None:
                                cfn_args["Tags"] = cfn_tags

                            response = my_cfn.update_stack(**cfn_args)
                        except ClientError as e:
                            if e.response["Error"]["Code"] == "ValidationError":
                                if "No updates are to be performed." in str(e):
                                    # No changes made to Config rule definition, so CloudFormation won't do anything.
                                    print(f"[{my_session.region_name}]: No changes to Config Rule.")
                                else:
                                    # Something unexpected has gone wrong.  Emit an error and bail.
                                    print(f"[{my_session.region_name}]:  {e}")
                                    return 1
                            else:
                                raise
                    except ClientError as e:
                        # If we're in the exception, the stack does not exist and we should create it.
                        print(f"[{my_session.region_name}]: Creating CloudFormation Stack for " + rule_name)
                        cfn_args = {
                            "StackName": my_stack_name,
                            "TemplateBody": open(cfn_body, "r").read(),
                            "Parameters": my_params,
                        }

                        if cfn_tags is not None:
                            cfn_args["Tags"] = cfn_tags

                        response = my_cfn.create_stack(**cfn_args)

                    # wait for changes to propagate.
                    self.__wait_for_cfn_stack(my_cfn, my_stack_name)

                # Cloudformation is not supporting tagging config rule currently.
                if cfn_tags is not None and len(cfn_tags) > 0:
                    self.__tag_config_rule(rule_name, cfn_tags, my_session)

                continue

            print(f"[{my_session.region_name}]: Found Custom Rule.")

            s3_src = ""
            s3_dst = self.__upload_function_code(rule_name, rule_params, account_id, my_session, code_bucket_name)

            # create CFN Parameters for Custom Rules
            lambdaRoleArn = ""
            if self.args.lambda_role_arn:
                print(f"[{my_session.region_name}]: Existing IAM Role provided: " + self.args.lambda_role_arn)
                lambdaRoleArn = self.args.lambda_role_arn
            elif self.args.lambda_role_name:
                print(f"[{my_session.region_name}]: Building IAM Role ARN from Name: " + self.args.lambda_role_name)
                arn = f"arn:{partition}:iam::{account_id}:role/{self.args.lambda_role_name}"
                lambdaRoleArn = arn

            if self.args.boundary_policy_arn:
                print(f"[{my_session.region_name}]: Boundary Policy provided: " + self.args.boundary_policy_arn)
                boundaryPolicyArn = self.args.boundary_policy_arn
            else:
                boundaryPolicyArn = ""

            try:
                rule_description = rule_params["Description"]
            except KeyError:
                rule_description = rule_name

            my_params = [
                {
                    "ParameterKey": "RuleName",
                    "ParameterValue": rule_name,
                },
                {
                    "ParameterKey": "RuleLambdaName",
                    "ParameterValue": self.__get_lambda_name(rule_name, rule_params),
                },
                {
                    "ParameterKey": "Description",
                    "ParameterValue": rule_description,
                },
                {
                    "ParameterKey": "LambdaRoleArn",
                    "ParameterValue": lambdaRoleArn,
                },
                {
                    "ParameterKey": "BoundaryPolicyArn",
                    "ParameterValue": boundaryPolicyArn,
                },
                {
                    "ParameterKey": "SourceBucket",
                    "ParameterValue": code_bucket_name,
                },
                {
                    "ParameterKey": "SourcePath",
                    "ParameterValue": s3_dst,
                },
                {
                    "ParameterKey": "SourceRuntime",
                    "ParameterValue": self.__get_runtime_string(rule_params),
                },
                {
                    "ParameterKey": "SourceEvents",
                    "ParameterValue": source_events,
                },
                {
                    "ParameterKey": "SourcePeriodic",
                    "ParameterValue": source_periodic,
                },
                {
                    "ParameterKey": "SourceInputParameters",
                    "ParameterValue": json.dumps(combined_input_parameters),
                },
                {
                    "ParameterKey": "SourceHandler",
                    "ParameterValue": self.__get_handler(rule_name, rule_params),
                },
                {
                    "ParameterKey": "Timeout",
                    "ParameterValue": str(self.args.lambda_timeout),
                },
            ]
            layers = self.__get_lambda_layers(my_session, self.args, rule_params)

            if self.args.lambda_layers:
                additional_layers = self.args.lambda_layers.split(",")
                layers.extend(additional_layers)

            if layers:
                my_params.append({"ParameterKey": "Layers", "ParameterValue": ",".join(layers)})

            if self.args.lambda_security_groups and self.args.lambda_subnets:
                my_params.append(
                    {
                        "ParameterKey": "SecurityGroupIds",
                        "ParameterValue": self.args.lambda_security_groups,
                    }
                )
                my_params.append(
                    {
                        "ParameterKey": "SubnetIds",
                        "ParameterValue": self.args.lambda_subnets,
                    }
                )

            # create json of CFN template
            cfn_body = os.path.join(path.dirname(__file__), "template", "configRule.json")
            template_body = open(cfn_body, "r").read()
            json_body = json.loads(template_body)

            remediation = ""
            if "Remediation" in rule_params:
                remediation = self.__create_remediation_cloudformation_block(rule_params["Remediation"])
                json_body["Resources"]["Remediation"] = remediation

                if "SSMAutomation" in rule_params:
                    ##AWS needs to build the SSM before the Config Rule
                    resource_depends_on = [
                        "rdkConfigRule",
                        self.__get_alphanumeric_rule_name(rule_name + "RemediationAction"),
                    ]
                    remediation["DependsOn"] = resource_depends_on
                    # Add JSON Reference to SSM Document { "Ref" : "MyEC2Instance" }
                    remediation["Properties"]["TargetId"] = {
                        "Ref": self.__get_alphanumeric_rule_name(rule_name + "RemediationAction")
                    }

            if "SSMAutomation" in rule_params:
                print(f"[{my_session.region_name}]: Building SSM Automation Section")

                ssm_automation = self.__create_automation_cloudformation_block(rule_params["SSMAutomation"], rule_name)
                json_body["Resources"][
                    self.__get_alphanumeric_rule_name(rule_name + "RemediationAction")
                ] = ssm_automation
                if "IAM" in rule_params["SSMAutomation"]:
                    print("Lets Build IAM Role and Policy")
                    # TODO Check For IAM Settings
                    json_body["Resources"]["Remediation"]["Properties"]["Parameters"]["AutomationAssumeRole"][
                        "StaticValue"
                    ]["Values"] = [
                        {
                            "Fn::GetAtt": [
                                self.__get_alphanumeric_rule_name(rule_name + "Role"),
                                "Arn",
                            ]
                        }
                    ]

                    (
                        ssm_iam_role,
                        ssm_iam_policy,
                    ) = self.__create_automation_iam_cloudformation_block(rule_params["SSMAutomation"], rule_name)
                    json_body["Resources"][self.__get_alphanumeric_rule_name(rule_name + "Role")] = ssm_iam_role
                    json_body["Resources"][self.__get_alphanumeric_rule_name(rule_name + "Policy")] = ssm_iam_policy

            # debugging
            # print(json.dumps(json_body, indent=2))

            # deploy config rule
            my_cfn = my_session.client("cloudformation")
            try:
                my_stack_name = self.__get_stack_name_from_rule_name(rule_name)
                my_stack = my_cfn.describe_stacks(StackName=my_stack_name)
                # If we've gotten here, stack exists and we should update it.
                print(f"[{my_session.region_name}]: Updating CloudFormation Stack for " + rule_name)
                try:
                    cfn_args = {
                        "StackName": my_stack_name,
                        "TemplateBody": json.dumps(json_body, indent=2),
                        "Parameters": my_params,
                        "Capabilities": ["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
                    }

                    # If no tags key is specified, or if the tags dict is empty
                    if cfn_tags is not None:
                        cfn_args["Tags"] = cfn_tags

                    response = my_cfn.update_stack(**cfn_args)
                except ClientError as e:
                    if e.response["Error"]["Code"] == "ValidationError":
                        if "No updates are to be performed." in str(e):
                            # No changes made to Config rule definition, so CloudFormation won't do anything.
                            print(f"[{my_session.region_name}]: No changes to Config Rule.")
                        else:
                            # Something unexpected has gone wrong.  Emit an error and bail.
                            print(f"[{my_session.region_name}]: Validation Error on CFN\n")
                            print(f"[{my_session.region_name}]: " + json.dumps(cfn_args) + "\n")
                            print(f"[{my_session.region_name}]: {e}\n")
                            return 1
                    else:
                        raise

                my_lambda_arn = self.__get_lambda_arn_for_stack(my_stack_name)

                print(f"[{my_session.region_name}]: Publishing Lambda code...")
                my_lambda_client = my_session.client("lambda")
                my_lambda_client.update_function_code(
                    FunctionName=my_lambda_arn,
                    S3Bucket=code_bucket_name,
                    S3Key=s3_dst,
                    Publish=True,
                )
                print(f"[{my_session.region_name}]: Lambda code updated.")
            except ClientError as e:
                # If we're in the exception, the stack does not exist and we should create it.
                print(f"[{my_session.region_name}]: Creating CloudFormation Stack for " + rule_name)
                cfn_args = {
                    "StackName": my_stack_name,
                    "TemplateBody": json.dumps(json_body, indent=2),
                    "Parameters": my_params,
                    "Capabilities": ["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
                }

                if cfn_tags is not None:
                    cfn_args["Tags"] = cfn_tags

                response = my_cfn.create_stack(**cfn_args)

            # wait for changes to propagate.
            self.__wait_for_cfn_stack(my_cfn, my_stack_name)

            # Cloudformation is not supporting tagging config rule currently.
            if cfn_tags is not None and len(cfn_tags) > 0:
                self.__tag_config_rule(rule_name, cfn_tags, my_session)

        print(f"[{my_session.region_name}]: Config deploy complete.")

        return 0

    def deploy_organization(self):
        self.__parse_deploy_organization_args()

        # get the rule names
        rule_names = self.__get_rule_list_for_command()

        # run the deploy code
        print("Running Organization deploy!")

        # create custom session based on whatever credentials are available to us
        my_session = self.__get_boto_session()

        # get accountID
        identity_details = self.__get_caller_identity_details(my_session)
        account_id = identity_details["account_id"]
        partition = identity_details["partition"]

        if self.args.custom_code_bucket:
            code_bucket_name = self.args.custom_code_bucket
        else:
            code_bucket_name = code_bucket_prefix + account_id + "-" + my_session.region_name

        # If we're only deploying the Lambda functions (and role + permissions), branch here.  Someday the "main" execution path should use the same generated CFN templates for single-account deployment.
        if self.args.functions_only:
            print("We don't handle Function Only deployment for Organizations")
            sys.exit(1)

        # If we're deploying both the functions and the Config rules, run the following process:
        for rule_name in rule_names:
            rule_params, cfn_tags = self.__get_rule_parameters(rule_name)

            # create CFN Parameters common for Managed and Custom
            source_events = "NONE"
            if "Remediation" in rule_params:
                print(
                    f"WARNING: Organization Rules with Remediation is not supported at the moment. {rule_name} will be deployed without auto-remediation."
                )

            if "SourceEvents" in rule_params:
                source_events = rule_params["SourceEvents"]

            source_periodic = "NONE"
            if "SourcePeriodic" in rule_params:
                source_periodic = rule_params["SourcePeriodic"]

            combined_input_parameters = {}
            if "InputParameters" in rule_params:
                combined_input_parameters.update(json.loads(rule_params["InputParameters"]))

            if "OptionalParameters" in rule_params:
                # Remove empty parameters
                keys_to_delete = []
                optional_parameters_json = json.loads(rule_params["OptionalParameters"])
                for key, value in optional_parameters_json.items():
                    if not value:
                        keys_to_delete.append(key)
                for key in keys_to_delete:
                    del optional_parameters_json[key]
                combined_input_parameters.update(optional_parameters_json)

            if self.args.excluded_accounts or "ExcludedAccounts" in rule_params:
                combined_excluded_accounts_set = set(
                    rule_params.get("ExcludedAccounts", "").split(",") + self.args.excluded_accounts
                )
                combined_excluded_accounts_str = ",".join(combined_excluded_accounts_set)
            else:
                combined_excluded_accounts_str = ""

            if "SourceIdentifier" in rule_params:
                print("Found Managed Rule.")
                # create CFN Parameters for Managed Rules

                try:
                    rule_description = rule_params["Description"]
                except KeyError:
                    rule_description = rule_name
                my_params = [
                    {
                        "ParameterKey": "RuleName",
                        "ParameterValue": rule_name,
                    },
                    {
                        "ParameterKey": "Description",
                        "ParameterValue": rule_description,
                    },
                    {
                        "ParameterKey": "SourceEvents",
                        "ParameterValue": source_events,
                    },
                    {
                        "ParameterKey": "SourcePeriodic",
                        "ParameterValue": source_periodic,
                    },
                    {
                        "ParameterKey": "SourceInputParameters",
                        "ParameterValue": json.dumps(combined_input_parameters),
                    },
                    {
                        "ParameterKey": "SourceIdentifier",
                        "ParameterValue": rule_params["SourceIdentifier"],
                    },
                    {
                        "ParameterKey": "ExcludedAccounts",
                        "ParameterValue": combined_excluded_accounts_str,
                    },
                ]
                my_cfn = my_session.client("cloudformation")

                # deploy config rule
                cfn_body = os.path.join(
                    path.dirname(__file__),
                    "template",
                    "configManagedRuleOrganization.json",
                )

                try:
                    my_stack_name = self.__get_stack_name_from_rule_name(rule_name)
                    my_stack = my_cfn.describe_stacks(StackName=my_stack_name)
                    # If we've gotten here, stack exists and we should update it.
                    print("Updating CloudFormation Stack for " + rule_name)
                    try:
                        cfn_args = {
                            "StackName": my_stack_name,
                            "TemplateBody": open(cfn_body, "r").read(),
                            "Parameters": my_params,
                        }

                        # If no tags key is specified, or if the tags dict is empty
                        if cfn_tags is not None:
                            cfn_args["Tags"] = cfn_tags

                        response = my_cfn.update_stack(**cfn_args)
                    except ClientError as e:
                        if e.response["Error"]["Code"] == "ValidationError":
                            if "No updates are to be performed." in str(e):
                                # No changes made to Config rule definition, so CloudFormation won't do anything.
                                print("No changes to Config Rule.")
                            else:
                                # Something unexpected has gone wrong.  Emit an error and bail.
                                print(e)
                                return 1
                        else:
                            raise
                except ClientError as e:
                    # If we're in the exception, the stack does not exist and we should create it.
                    print("Creating CloudFormation Stack for " + rule_name)
                    cfn_args = {
                        "StackName": my_stack_name,
                        "TemplateBody": open(cfn_body, "r").read(),
                        "Parameters": my_params,
                    }

                    if cfn_tags is not None:
                        cfn_args["Tags"] = cfn_tags

                    response = my_cfn.create_stack(**cfn_args)

                # wait for changes to propagate.
                self.__wait_for_cfn_stack(my_cfn, my_stack_name)

                # Cloudformation is not supporting tagging config rule currently.
                if cfn_tags is not None and len(cfn_tags) > 0:
                    print(
                        "WARNING: Tagging is not supported for organization config rules. Only the cloudformation template will be tagged."
                    )

                continue

            print("Found Custom Rule.")

            s3_src = ""
            s3_dst = self.__upload_function_code(rule_name, rule_params, account_id, my_session, code_bucket_name)

            # create CFN Parameters for Custom Rules
            lambdaRoleArn = ""
            if self.args.lambda_role_arn:
                print("Existing IAM Role provided: " + self.args.lambda_role_arn)
                lambdaRoleArn = self.args.lambda_role_arn
            elif self.args.lambda_role_name:
                print(f"[{my_session.region_name}]: Building IAM Role ARN from Name: " + self.args.lambda_role_name)
                arn = f"arn:{partition}:iam::{account_id}:role/{self.args.lambda_role_name}"
                lambdaRoleArn = arn

            if self.args.boundary_policy_arn:
                print("Boundary Policy provided: " + self.args.boundary_policy_arn)
                boundaryPolicyArn = self.args.boundary_policy_arn
            else:
                boundaryPolicyArn = ""

            try:
                rule_description = rule_params["Description"]
            except KeyError:
                rule_description = rule_name

            my_params = [
                {
                    "ParameterKey": "RuleName",
                    "ParameterValue": rule_name,
                },
                {
                    "ParameterKey": "RuleLambdaName",
                    "ParameterValue": self.__get_lambda_name(rule_name, rule_params),
                },
                {
                    "ParameterKey": "Description",
                    "ParameterValue": rule_description,
                },
                {
                    "ParameterKey": "LambdaRoleArn",
                    "ParameterValue": lambdaRoleArn,
                },
                {
                    "ParameterKey": "BoundaryPolicyArn",
                    "ParameterValue": boundaryPolicyArn,
                },
                {
                    "ParameterKey": "SourceBucket",
                    "ParameterValue": code_bucket_name,
                },
                {
                    "ParameterKey": "SourcePath",
                    "ParameterValue": s3_dst,
                },
                {
                    "ParameterKey": "SourceRuntime",
                    "ParameterValue": self.__get_runtime_string(rule_params),
                },
                {
                    "ParameterKey": "SourceEvents",
                    "ParameterValue": source_events,
                },
                {
                    "ParameterKey": "SourcePeriodic",
                    "ParameterValue": source_periodic,
                },
                {
                    "ParameterKey": "SourceInputParameters",
                    "ParameterValue": json.dumps(combined_input_parameters),
                },
                {
                    "ParameterKey": "SourceHandler",
                    "ParameterValue": self.__get_handler(rule_name, rule_params),
                },
                {
                    "ParameterKey": "Timeout",
                    "ParameterValue": str(self.args.lambda_timeout),
                },
                {
                    "ParameterKey": "ExcludedAccounts",
                    "ParameterValue": combined_excluded_accounts_str,
                },
            ]
            layers = self.__get_lambda_layers(my_session, self.args, rule_params)

            if self.args.lambda_layers:
                additional_layers = self.args.lambda_layers.split(",")
                layers.extend(additional_layers)

            if layers:
                my_params.append({"ParameterKey": "Layers", "ParameterValue": ",".join(layers)})

            if self.args.lambda_security_groups and self.args.lambda_subnets:
                my_params.append(
                    {
                        "ParameterKey": "SecurityGroupIds",
                        "ParameterValue": self.args.lambda_security_groups,
                    }
                )
                my_params.append(
                    {
                        "ParameterKey": "SubnetIds",
                        "ParameterValue": self.args.lambda_subnets,
                    }
                )

            # create json of CFN template
            cfn_body = os.path.join(path.dirname(__file__), "template", "configRuleOrganization.json")
            template_body = open(cfn_body, "r").read()
            json_body = json.loads(template_body)

            # debugging
            # print(json.dumps(json_body, indent=2))

            # deploy config rule
            my_cfn = my_session.client("cloudformation")
            try:
                my_stack_name = self.__get_stack_name_from_rule_name(rule_name)
                my_stack = my_cfn.describe_stacks(StackName=my_stack_name)
                # If we've gotten here, stack exists and we should update it.
                print("Updating CloudFormation Stack for " + rule_name)
                try:
                    cfn_args = {
                        "StackName": my_stack_name,
                        "TemplateBody": json.dumps(json_body),
                        "Parameters": my_params,
                        "Capabilities": ["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
                    }

                    # If no tags key is specified, or if the tags dict is empty
                    if cfn_tags is not None:
                        cfn_args["Tags"] = cfn_tags

                    response = my_cfn.update_stack(**cfn_args)
                except ClientError as e:
                    if e.response["Error"]["Code"] == "ValidationError":
                        if "No updates are to be performed." in str(e):
                            # No changes made to Config rule definition, so CloudFormation won't do anything.
                            print("No changes to Config Rule.")
                        else:
                            # Something unexpected has gone wrong.  Emit an error and bail.
                            print("Validation Error on CFN")
                            print(json.dumps(cfn_args))
                            print(e)
                            return 1
                    else:
                        raise

                my_lambda_arn = self.__get_lambda_arn_for_stack(my_stack_name)

                print("Publishing Lambda code...")
                my_lambda_client = my_session.client("lambda")
                my_lambda_client.update_function_code(
                    FunctionName=my_lambda_arn,
                    S3Bucket=code_bucket_name,
                    S3Key=s3_dst,
                    Publish=True,
                )
                print("Lambda code updated.")
            except ClientError as e:
                # If we're in the exception, the stack does not exist and we should create it.
                print("Creating CloudFormation Stack for " + rule_name)
                cfn_args = {
                    "StackName": my_stack_name,
                    "TemplateBody": json.dumps(json_body),
                    "Parameters": my_params,
                    "Capabilities": ["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
                }

                if cfn_tags is not None:
                    cfn_args["Tags"] = cfn_tags

                response = my_cfn.create_stack(**cfn_args)

            # wait for changes to propagate.
            self.__wait_for_cfn_stack(my_cfn, my_stack_name)

            # Cloudformation is not supporting tagging config rule currently.
            if cfn_tags is not None and len(cfn_tags) > 0:
                print(
                    "WARNING: Tagging is not supported for organization config rules. Only the cloudformation template will be tagged."
                )

        print("Config deploy complete.")

        return 0

    def export(self):
        self.__parse_export_args()

        # get the rule names
        rule_names = self.__get_rule_list_for_command("export")

        # run the export code
        print("Running export")

        for rule_name in rule_names:
            rule_params, cfn_tags = self.__get_rule_parameters(rule_name)

            if "SourceIdentifier" in rule_params:
                print("Found Managed Rule, Ignored.")
                print("Export support only Custom Rules.")
                continue

            source_events = []
            if "SourceEvents" in rule_params:
                source_events = [rule_params["SourceEvents"]]

            source_periodic = "NONE"
            if "SourcePeriodic" in rule_params:
                source_periodic = rule_params["SourcePeriodic"]

            combined_input_parameters = {}
            if "InputParameters" in rule_params:
                combined_input_parameters.update(json.loads(rule_params["InputParameters"]))

            if "OptionalParameters" in rule_params:
                # Remove empty parameters
                keys_to_delete = []
                optional_parameters_json = json.loads(rule_params["OptionalParameters"])
                for key, value in optional_parameters_json.items():
                    if not value:
                        keys_to_delete.append(key)
                for key in keys_to_delete:
                    del optional_parameters_json[key]
                combined_input_parameters.update(optional_parameters_json)

            print("Found Custom Rule.")
            s3_src = ""
            s3_dst = self.__package_function_code(rule_name, rule_params)

            layers = []
            rdk_lib_version = "0"
            my_session = self.__get_boto_session()
            layers = self.__get_lambda_layers(my_session, self.args, rule_params)

            if self.args.lambda_layers:
                additional_layers = self.args.lambda_layers.split(",")
                layers.extend(additional_layers)

            subnet_ids = []
            security_group_ids = []
            if self.args.lambda_security_groups:
                security_group_ids = self.args.lambda_security_groups.split(",")

            if self.args.lambda_subnets:
                subnet_ids = self.args.lambda_subnets.split(",")

            lambda_role_arn = "NONE"
            if self.args.lambda_role_arn:
                print("Existing IAM Role provided: " + self.args.lambda_role_arn)
                lambda_role_arn = self.args.lambda_role_arn

            my_params = {
                "rule_name": rule_name,
                "rule_lambda_name": self.__get_lambda_name(rule_name, rule_params),
                "source_runtime": self.__get_runtime_string(rule_params),
                "source_events": source_events,
                "source_periodic": source_periodic,
                "source_input_parameters": json.dumps(combined_input_parameters),
                "source_handler": self.__get_handler(rule_name, rule_params),
                "subnet_ids": subnet_ids,
                "security_group_ids": security_group_ids,
                "lambda_layers": layers,
                "lambda_role_arn": lambda_role_arn,
                "lambda_timeout": str(self.args.lambda_timeout),
            }

            params_file_path = os.path.join(os.getcwd(), rules_dir, rule_name, rule_name.lower() + ".tfvars.json")
            parameters_file = open(params_file_path, "w")
            json.dump(my_params, parameters_file, indent=4)
            parameters_file.close()
            # create json of CFN template
            print(self.args.format + " version: " + self.args.version)
            tf_file_body = os.path.join(
                path.dirname(__file__),
                "template",
                self.args.format,
                self.args.version,
                "config_rule.tf",
            )
            tf_file_path = os.path.join(os.getcwd(), rules_dir, rule_name, rule_name.lower() + "_rule.tf")
            shutil.copy(tf_file_body, tf_file_path)

            variables_file_body = os.path.join(
                path.dirname(__file__),
                "template",
                self.args.format,
                self.args.version,
                "variables.tf",
            )
            variables_file_path = os.path.join(os.getcwd(), rules_dir, rule_name, rule_name.lower() + "_variables.tf")
            shutil.copy(variables_file_body, variables_file_path)
            print("Export completed.This will generate three .tf files.")

    def test_local(self):
        print("Running local test!")
        tests_successful = True

        args = self.__parse_test_args()

        # Construct our list of rules to test.
        rule_names = self.__get_rule_list_for_command()

        for rule_name in rule_names:
            rule_params, rule_tags = self.__get_rule_parameters(rule_name)
            if rule_params["SourceRuntime"] not in (
                "python3.7",
                "python3.7-lib",
                "python3.8",
                "python3.8-lib",
                "python3.9",
                "python3.9-lib",
                "python3.10",
                "python3.10-lib",
                "python3.11",
                "python3.11-lib",
            ):
                print("Skipping " + rule_name + " - Runtime not supported for local testing.")
                continue

            print("Testing " + rule_name)
            test_dir = os.path.join(os.getcwd(), rules_dir, rule_name)
            print("Looking for tests in " + test_dir)

            if args.verbose == True:
                results = unittest.TextTestRunner(buffer=False, verbosity=2).run(self.__create_test_suite(test_dir))
            else:
                results = unittest.TextTestRunner(buffer=True, verbosity=2).run(self.__create_test_suite(test_dir))

            print(results)

            tests_successful = tests_successful and results.wasSuccessful()
        return int(not tests_successful)

    def test_remote(self):
        print("Running test_remote!")
        self.__parse_test_args()

        # Construct our list of rules to test.
        rule_names = self.__get_rule_list_for_command()

        # Create our Lambda client.
        my_session = self.__get_boto_session()
        my_lambda_client = my_session.client("lambda")

        for rule_name in rule_names:
            print("Testing " + rule_name)

            # Get CI JSON from either the CLI or one of the stored templates.
            my_cis = self.__get_test_CIs(rule_name)

            my_parameters = {}
            if self.args.test_parameters:
                my_parameters = json.loads(self.args.test_parameters)

            for my_ci in my_cis:
                print("\t\tTesting CI " + my_ci["resourceType"])

                # Generate test event from templates
                test_event = json.load(
                    open(
                        os.path.join(path.dirname(__file__), "template", event_template_filename),
                        "r",
                    ),
                    strict=False,
                )
                my_invoking_event = json.loads(test_event["invokingEvent"])
                my_invoking_event["configurationItem"] = my_ci
                my_invoking_event["notificationCreationTime"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
                test_event["invokingEvent"] = json.dumps(my_invoking_event)
                test_event["ruleParameters"] = json.dumps(my_parameters)

                # Get the Lambda function associated with the Rule
                stack_name = self.__get_stack_name_from_rule_name(rule_name)
                my_lambda_arn = self.__get_lambda_arn_for_stack(stack_name)

                # Call Lambda function with test event.
                result = my_lambda_client.invoke(
                    FunctionName=my_lambda_arn,
                    InvocationType="RequestResponse",
                    LogType="Tail",
                    Payload=json.dumps(test_event),
                )

                # If there's an error dump execution logs to the terminal, if not print out the value returned by the lambda function.
                if "FunctionError" in result:
                    print(base64.b64decode(str(result["LogResult"])))
                else:
                    print("\t\t\t" + result["Payload"].read())
                    if self.args.verbose:
                        print(base64.b64decode(str(result["LogResult"])))
        return 0

    def status(self):
        print("Running status!")
        return 0

    def sample_ci(self):
        self.args = get_sample_ci_parser().parse_args(self.args.command_args, self.args)

        my_test_ci = TestCI(self.args.ci_type)
        print(json.dumps(my_test_ci.get_json(), indent=4))
        print(
            f"For more info, try checking: https://github.com/awslabs/aws-config-resource-schema/blob/master/config/properties/resource-types/"
        )

    def logs(self):
        self.args = get_logs_parser().parse_args(self.args.command_args, self.args)

        self.args.rulename = self.__clean_rule_name(self.args.rulename)

        my_session = self.__get_boto_session()
        cw_logs = my_session.client("logs")
        log_group_name = self.__get_log_group_name()

        # Retrieve the last number of log events as specified by the user.
        try:
            log_streams = cw_logs.describe_log_streams(
                logGroupName=log_group_name,
                orderBy="LastEventTime",
                descending=True,
                limit=int(self.args.number),  # This is the worst-case scenario if there is only one event per stream
            )

            # Sadly we can't just use filter_log_events, since we don't know the timestamps yet and filter_log_events doesn't appear to support ordering.
            my_events = self.__get_log_events(cw_logs, log_streams, int(self.args.number))

            latest_timestamp = 0

            if my_events is None:
                print("No Events to display.")
                return 0

            for event in my_events:
                if event["timestamp"] > latest_timestamp:
                    latest_timestamp = event["timestamp"]

                self.__print_log_event(event)

            if self.args.follow:
                try:
                    while True:
                        # Wait 2 seconds
                        time.sleep(2)

                        # Get all events between now and the timestamp of the most recent event.
                        my_new_events = cw_logs.filter_log_events(
                            logGroupName=log_group_name,
                            startTime=latest_timestamp + 1,
                            endTime=int(time.time()) * 1000,
                            interleaved=True,
                        )

                        for event in my_new_events["events"]:
                            if "timestamp" in event:
                                # Get the timestamp on the most recent event.
                                if event["timestamp"] > latest_timestamp:
                                    latest_timestamp = event["timestamp"]

                                # Print the event.
                                self.__print_log_event(event)
                except KeyboardInterrupt as k:
                    sys.exit(0)

        except cw_logs.exceptions.ResourceNotFoundException as e:
            print(e.response["Error"]["Message"])

    def rulesets(self):
        self.args = get_rulesets_parser().parse_args(self.args.command_args, self.args)

        if self.args.subcommand in ["add", "remove"] and (not self.args.ruleset or not self.args.rulename):
            print("You must specify a ruleset name and a rule for the `add` and `remove` commands.")
            return 1

        if self.args.subcommand == "list":
            self.__list_rulesets()
        elif self.args.subcommand == "add":
            self.__add_ruleset_rule(self.args.ruleset, self.args.rulename)
        elif self.args.subcommand == "remove":
            self.__remove_ruleset_rule(self.args.ruleset, self.args.rulename)
        else:
            print("Unknown subcommand.")

    def create_terraform_template(self):
        self.args = get_create_rule_template_parser().parse_args(self.args.command_args, self.args)

        if self.args.rulesets:
            self.args.rulesets = self.args.rulesets.split(",")

        print("Generating Terraform template!")

        template = self.__generate_terraform_shell(self.args)

        rule_names = self.__get_rule_list_for_command()

        for rule_name in rule_names:
            rule_input_params = self.__generate_rule_terraform_params(rule_name)
            rule_def = self.__generate_rule_terraform(rule_name)
            template.append(rule_input_params)
            template.append(rule_def)

        output_file = open(self.args.output_file, "w")
        output_file.write(json.dumps(template, indent=2))
        print("CloudFormation template written to " + self.args.output_file)

    def create_rule_template(self):
        self.args = get_create_rule_template_parser().parse_args(self.args.command_args, self.args)

        if self.args.rulesets:
            self.args.rulesets = self.args.rulesets.split(",")

        script_for_tag = ""

        print("Generating CloudFormation template!")

        # First add the common elements - description, parameters, and resource section header
        template = {}
        template["AWSTemplateFormatVersion"] = "2010-09-09"
        template[
            "Description"
        ] = "AWS CloudFormation template to create custom AWS Config rules. You will be billed for the AWS resources used if you create a stack from this template."

        optional_parameter_group = {"Label": {"default": "Optional"}, "Parameters": []}

        required_parameter_group = {"Label": {"default": "Required"}, "Parameters": []}

        parameters = {}
        parameters["LambdaAccountId"] = {}
        parameters["LambdaAccountId"]["Description"] = "Account ID that contains Lambda functions for Config Rules."
        parameters["LambdaAccountId"]["Type"] = "String"
        parameters["LambdaAccountId"]["MinLength"] = "12"
        parameters["LambdaAccountId"]["MaxLength"] = "12"

        resources = {}
        conditions = {}

        if not self.args.rules_only:
            # Create Config Role
            resources["ConfigRole"] = {}
            resources["ConfigRole"]["Type"] = "AWS::IAM::Role"
            resources["ConfigRole"]["DependsOn"] = "ConfigBucket"
            resources["ConfigRole"]["Properties"] = {
                "RoleName": config_role_name,
                "Path": "/rdk/",
                "ManagedPolicyArns": [
                    {"Fn::Sub": "arn:${AWS::Partition}:iam::aws:policy/service-role/AWS_ConfigRole"},
                    {"Fn::Sub": "arn:${AWS::Partition}:iam::aws:policy/ReadOnlyAccess"},
                ],
                "AssumeRolePolicyDocument": CONFIG_ROLE_ASSUME_ROLE_POLICY_DOCUMENT,
                "Policies": [
                    {
                        "PolicyName": "DeliveryPermission",
                        "PolicyDocument": CONFIG_ROLE_POLICY_DOCUMENT,
                    }
                ],
            }

            # Create Bucket for Config Data
            resources["ConfigBucket"] = {
                "Type": "AWS::S3::Bucket",
                "Properties": {"BucketName": {"Fn::Sub": config_bucket_prefix + "-${AWS::AccountId}-${AWS::Region}"}},
            }

            # Create ConfigurationRecorder and DeliveryChannel
            resources["ConfigurationRecorder"] = {
                "Type": "AWS::Config::ConfigurationRecorder",
                "Properties": {
                    "Name": "default",
                    "RoleARN": {"Fn::GetAtt": ["ConfigRole", "Arn"]},
                    "RecordingGroup": {
                        "AllSupported": True,
                        "IncludeGlobalResourceTypes": True,
                    },
                },
            }
            if self.args.config_role_arn:
                resources["ConfigurationRecorder"]["Properties"]["RoleARN"] = self.args.config_role_arn

            resources["DeliveryChannel"] = {
                "Type": "AWS::Config::DeliveryChannel",
                "Properties": {
                    "Name": "default",
                    "S3BucketName": {"Ref": "ConfigBucket"},
                    "ConfigSnapshotDeliveryProperties": {"DeliveryFrequency": "One_Hour"},
                },
            }

        # Next, go through each rule in our rule list and add the CFN to deploy it.
        rule_names = self.__get_rule_list_for_command()
        for rule_name in rule_names:
            params, tags = self.__get_rule_parameters(rule_name)
            input_params = json.loads(params["InputParameters"])
            for input_param in input_params:
                cfn_param = {}
                cfn_param["Description"] = (
                    "Pass-through to required Input Parameter " + input_param + " for Config Rule " + rule_name
                )
                if len(str(input_params[input_param]).strip()) == 0:
                    default = "<REQUIRED>"
                else:
                    default = str(input_params[input_param])
                cfn_param["Default"] = default
                cfn_param["Type"] = "String"
                cfn_param["MinLength"] = 1
                cfn_param["ConstraintDescription"] = "This parameter is required."

                param_name = self.__get_alphanumeric_rule_name(rule_name) + input_param
                parameters[param_name] = cfn_param
                required_parameter_group["Parameters"].append(param_name)

            if "OptionalParameters" in params:
                optional_params = json.loads(params["OptionalParameters"])
                for optional_param in optional_params:
                    cfn_param = {}
                    cfn_param["Description"] = (
                        "Pass-through to optional Input Parameter " + optional_param + " for Config Rule " + rule_name
                    )
                    cfn_param["Default"] = optional_params[optional_param]
                    cfn_param["Type"] = "String"

                    param_name = self.__get_alphanumeric_rule_name(rule_name) + optional_param

                    parameters[param_name] = cfn_param
                    optional_parameter_group["Parameters"].append(param_name)

                    conditions[param_name] = {"Fn::Not": [{"Fn::Equals": ["", {"Ref": param_name}]}]}

            config_rule = {}
            config_rule["Type"] = "AWS::Config::ConfigRule"
            if not self.args.rules_only:
                config_rule["DependsOn"] = "DeliveryChannel"

            properties = {}
            source = {}
            source["SourceDetails"] = []

            properties["ConfigRuleName"] = rule_name
            try:
                properties["Description"] = params["Description"]
            except KeyError:
                properties["Description"] = rule_name

            # Create the SourceDetails stanza.
            if "SourceEvents" in params:
                # If there are SourceEvents specified for the Rule, generate the Scope clause.
                source_events = params["SourceEvents"].split(",")
                properties["Scope"] = {"ComplianceResourceTypes": source_events}

                # Also add the appropriate event source.
                source["SourceDetails"].append(
                    {
                        "EventSource": "aws.config",
                        "MessageType": "ConfigurationItemChangeNotification",
                    }
                )
            if "SourcePeriodic" in params:
                source["SourceDetails"].append(
                    {
                        "EventSource": "aws.config",
                        "MessageType": "ScheduledNotification",
                        "MaximumExecutionFrequency": params["SourcePeriodic"],
                    }
                )

            # If it's a Managed Rule it will have a SourceIdentifier string in the params and we need to set the source appropriately.  Otherwise, set the source to our custom lambda function.
            if "SourceIdentifier" in params:
                source["Owner"] = "AWS"
                source["SourceIdentifier"] = params["SourceIdentifier"]
                # Check the frequency of the managed rule if defined
                if "SourcePeriodic" in params:
                    properties["MaximumExecutionFrequency"] = params["SourcePeriodic"]
                del source["SourceDetails"]
            else:
                source["Owner"] = "CUSTOM_LAMBDA"
                source["SourceIdentifier"] = {
                    "Fn::Sub": "arn:${AWS::Partition}:lambda:${AWS::Region}:${LambdaAccountId}:function:"
                    + self.__get_lambda_name(rule_name, params)
                }

            properties["Source"] = source

            properties["InputParameters"] = {}

            if "InputParameters" in params:
                for required_param in json.loads(params["InputParameters"]):
                    cfn_param_name = self.__get_alphanumeric_rule_name(rule_name) + required_param
                    properties["InputParameters"][required_param] = {"Ref": cfn_param_name}

            if "OptionalParameters" in params:
                for optional_param in json.loads(params["OptionalParameters"]):
                    cfn_param_name = self.__get_alphanumeric_rule_name(rule_name) + optional_param
                    properties["InputParameters"][optional_param] = {
                        "Fn::If": [
                            cfn_param_name,
                            {"Ref": cfn_param_name},
                            {"Ref": "AWS::NoValue"},
                        ]
                    }

            config_rule["Properties"] = properties
            config_rule_resource_name = self.__get_alphanumeric_rule_name(rule_name) + "ConfigRule"
            resources[config_rule_resource_name] = config_rule

            # If Remediation create the remediation section with potential links to the SSM Details
            if "Remediation" in params:
                remediation = self.__create_remediation_cloudformation_block(params["Remediation"])
                remediation["DependsOn"] = [config_rule_resource_name]
                if not self.args.rules_only:
                    remediation["DependsOn"].append("ConfigRole")

                if "SSMAutomation" in params:
                    ssm_automation = self.__create_automation_cloudformation_block(params["SSMAutomation"], rule_name)
                    # AWS needs to build the SSM before the Config Rule
                    remediation["DependsOn"].append(self.__get_alphanumeric_rule_name(rule_name + "RemediationAction"))
                    # Add JSON Reference to SSM Document { "Ref" : "MyEC2Instance" }
                    remediation["Properties"]["TargetId"] = {
                        "Ref": self.__get_alphanumeric_rule_name(rule_name) + "RemediationAction"
                    }

                    if "IAM" in params["SSMAutomation"]:
                        print("Lets Build IAM Role and Policy For the SSM Document")
                        (
                            ssm_iam_role,
                            ssm_iam_policy,
                        ) = self.__create_automation_iam_cloudformation_block(params["SSMAutomation"], rule_name)
                        resources[self.__get_alphanumeric_rule_name(rule_name + "Role")] = ssm_iam_role
                        resources[self.__get_alphanumeric_rule_name(rule_name + "Policy")] = ssm_iam_policy
                        remediation["Properties"]["Parameters"]["AutomationAssumeRole"]["StaticValue"]["Values"] = [
                            {
                                "Fn::GetAtt": [
                                    self.__get_alphanumeric_rule_name(rule_name + "Role"),
                                    "Arn",
                                ]
                            }
                        ]
                        # Override the placeholder to associate the SSM Document Role with newly crafted role
                        resources[self.__get_alphanumeric_rule_name(rule_name + "RemediationAction")] = ssm_automation
                resources[self.__get_alphanumeric_rule_name(rule_name) + "Remediation"] = remediation

            if tags:
                tags_str = ""
                for tag in tags:
                    key = tag["Key"]
                    val = tag["Value"]
                    tags_str += f"Key={key},Value={val} "
                script_for_tag += (
                    "aws configservice tag-resource --resources-arn $(aws configservice describe-config-rules "
                    + f"--config-rule-names {rule_name} --query 'ConfigRules[0].ConfigRuleArn' | tr -d '\"') --tags {tags_str} \n"
                )

        template["Resources"] = resources
        template["Conditions"] = conditions
        template["Parameters"] = parameters
        template["Metadata"] = {
            "AWS::CloudFormation::Interface": {
                "ParameterGroups": [
                    {
                        "Label": {"default": "Lambda Account ID"},
                        "Parameters": ["LambdaAccountId"],
                    },
                    required_parameter_group,
                    optional_parameter_group,
                ],
                "ParameterLabels": {
                    "LambdaAccountId": {
                        "default": "REQUIRED: Account ID that contains Lambda Function(s) that back the Rules in this template."
                    }
                },
            }
        }

        output_file = open(self.args.output_file, "w")
        output_file.write(json.dumps(template, indent=2))
        print("CloudFormation template written to " + self.args.output_file)

        if script_for_tag:
            print("Found tags on config rules. Cloudformation do not support tagging config rule at the moment")
            print("Generating script for config rules tags")
            script_for_tag = "#! /bin/bash \n" + script_for_tag
            if self.args.tag_config_rules_script:
                with open(self.args.tag_config_rules_script, "w") as rsh:
                    rsh.write(script_for_tag)
            else:
                print("=========SCRIPT=========")
                print(script_for_tag)
                print("you can use flag [--tag-config-rules-script <file path> ] to output the script")

    def create_region_set(self):
        self.args = get_create_region_set_parser().parse_args(self.args.command_args, self.args)
        output_file = self.args.output_file
        output_dict = {
            "default": ["us-east-1", "us-west-1", "eu-north-1", "ap-southeast-1"],
            "aws-cn-region-set": ["cn-north-1", "cn-northwest-1"],
        }
        with open(f"{output_file}.yaml", "w+") as file:
            yaml.dump(output_dict, file, default_flow_style=False)

    def __generate_terraform_shell(self, args):
        return ""

    def __generate_rule_terraform(self, rule_name):
        return ""

    def __generate_rule_terraform_params(self, rule_name):
        return ""

    def __remove_ruleset_rule(self, ruleset, rulename):
        params, tags = self.__get_rule_parameters(rulename)
        if "RuleSets" in params:
            if self.args.ruleset in params["RuleSets"]:
                params["RuleSets"].remove(self.args.ruleset)
            else:
                print("Rule " + rulename + " is not in RuleSet " + ruleset)
        else:
            print("Rule " + rulename + " is not in any RuleSets")

        self.__write_params_file(rulename, params, tags)

        print(rulename + " removed from RuleSet " + ruleset)

    def __add_ruleset_rule(self, ruleset, rulename):
        params, tags = self.__get_rule_parameters(rulename)
        if "RuleSets" in params:
            if self.args.ruleset in params["RuleSets"]:
                print("Rule is already in the specified RuleSet.")
            else:
                params["RuleSets"].append(self.args.ruleset)
        else:
            rulesets = [self.args.ruleset]
            params["RuleSets"] = rulesets

        self.__write_params_file(rulename, params, tags)

        print(rulename + " added to RuleSet " + ruleset)

    def __list_rulesets(self):
        rulesets = []
        rules = []

        for obj_name in os.listdir("."):
            if obj_name.startswith("."):
                continue  # Skip hidden items
            params_file_path = os.path.join(".", obj_name, parameter_file_name)
            if os.path.isfile(params_file_path):
                parameters_file = open(params_file_path, "r")
                my_params = json.load(parameters_file)
                parameters_file.close()
                if "RuleSets" in my_params["Parameters"]:
                    rulesets.extend(my_params["Parameters"]["RuleSets"])

                    if self.args.ruleset in my_params["Parameters"]["RuleSets"]:
                        # print("Found rule! " + obj_name)
                        rules.append(obj_name)

        if self.args.ruleset:
            rules.sort()
            print("Rules in", self.args.ruleset, ": ")
            print(*rules, sep="\n")
        else:
            deduped = list(set(rulesets))
            deduped.sort()
            print("RuleSets: ", *deduped)

    def __get_template_dir(self):
        return os.path.join(path.dirname(__file__), "template")

    def __create_test_suite(self, test_dir):
        tests = []
        for top, dirs, filenames in os.walk(test_dir):
            for filename in fnmatch.filter(filenames, "*_test.py"):
                print(filename)
                sys.path.append(top)
                tests.append(filename[:-3])

        suites = [unittest.defaultTestLoader.loadTestsFromName(test) for test in tests]
        for suite in suites:
            print("Debug!")
            print(suite)

        return unittest.TestSuite(suites)

    def __clean_rule_name(self, rule_name):
        output = rule_name
        if output[-1:] == "/":
            print("Removing trailing '/'")
            output = output.rstrip("/")

        return output

    def __create_java_rule(self):
        src = os.path.join(path.dirname(__file__), "template", "runtime", "java8", "src")
        dst = os.path.join(os.getcwd(), rules_dir, self.args.rulename, "src")
        shutil.copytree(src, dst)

        src = os.path.join(path.dirname(__file__), "template", "runtime", "java8", "jars")
        dst = os.path.join(os.getcwd(), rules_dir, self.args.rulename, "jars")
        shutil.copytree(src, dst)

        src = os.path.join(path.dirname(__file__), "template", "runtime", "java8", "build.gradle")
        dst = os.path.join(os.getcwd(), rules_dir, self.args.rulename, "build.gradle")
        shutil.copyfile(src, dst)

    def __print_log_event(self, event):
        time_string = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(event["timestamp"] / 1000))

        rows = 24
        columns = 80
        if shutil.which("stty") is not None:
            try:
                rows, columns = os.popen("stty size", "r").read().split()
            except Exception as e:
                # This was probably being run in a headless test environment which had no stty.
                print("Using default terminal rows and columns.")
        else:
            print("stty not present -- using default terminal rows and columns.")

        line_wrap = int(columns) - 22
        message_lines = str(event["message"]).splitlines()
        formatted_lines = []

        for line in message_lines:
            line = line.replace("\t", "    ")
            formatted_lines.append("\n".join(line[i : i + line_wrap] for i in range(0, len(line), line_wrap)))

        message_string = "\n".join(formatted_lines)
        message_string = message_string.replace("\n", "\n                      ")

        print(time_string + " - " + message_string)

    def __get_log_events(self, my_client, log_streams, number_of_events):
        event_count = 0
        log_events = []
        for stream in log_streams["logStreams"]:
            # Retrieve the logs for this stream.
            events = my_client.get_log_events(
                logGroupName=self.__get_log_group_name(),
                logStreamName=stream["logStreamName"],
                limit=int(number_of_events),
            )
            # Go through the logs and add events to my output array.
            for event in events["events"]:
                log_events.append(event)
                event_count = event_count + 1

                # Once we have enough events, stop.
                if event_count >= number_of_events:
                    return log_events

        # If more records were requested than exist, return as many as we found.
        return log_events

    def __get_log_group_name(self):
        params, cfn_tags = self.__get_rule_parameters(self.args.rulename)

        return "/aws/lambda/" + self.__get_lambda_name(self.args.rulename, params)

    def __get_boto_session(self):
        session_args = {}

        if self.args.region:
            session_args["region_name"] = self.args.region

        if self.args.profile:
            session_args["profile_name"] = self.args.profile
        elif self.args.access_key_id and self.args.secret_access_key:
            session_args["aws_access_key_id"] = self.args.access_key_id
            session_args["aws_secret_access_key"] = self.args.secret_access_key

        return Session(**session_args)

    def __get_caller_identity_details(self, my_session):
        my_sts = my_session.client("sts")
        try:
            response = my_sts.get_caller_identity()
        except botocore.exceptions.ClientError:
            logging.error(
                "Unable to establish session to AWS. Make sure your CLI has access to valid AWS credentials and permissions to sts:GetCallerIdentity."
            )
            sys.exit(1)
        arn_split = response["Arn"].split(":")

        return {
            "account_id": response["Account"],
            "partition": arn_split[1],
            "region": arn_split[3],
        }

    def __get_stack_name_from_rule_name(self, rule_name):
        output = rule_name.replace("_", "")

        return output

    def __get_alphanumeric_rule_name(self, rule_name):
        output = rule_name.replace("_", "").replace("-", "")

        return output

    def __get_rule_list_for_command(self, Command="deploy"):
        rule_names = []
        if self.args.all:
            for obj_name in os.listdir("."):
                obj_path = os.path.join(".", obj_name)
                if os.path.isdir(obj_path) and not obj_name == "rdk":
                    for file_name in os.listdir(obj_path):
                        if obj_name not in rule_names:
                            if os.path.exists(os.path.join(obj_path, "parameters.json")):
                                rule_names.append(obj_name)
                            else:
                                if file_name.split(".")[0] == obj_name:
                                    rule_names.append(obj_name)
                                if os.path.exists(
                                    os.path.join(
                                        obj_path,
                                        "src",
                                        "main",
                                        "java",
                                        "com",
                                        "rdk",
                                        "RuleCode.java",
                                    )
                                ):
                                    rule_names.append(obj_name)
                                if os.path.exists(os.path.join(obj_path, "RuleCode.cs")):
                                    rule_names.append(obj_name)
        elif self.args.rulesets:
            for obj_name in os.listdir("."):
                params_file_path = os.path.join(".", obj_name, parameter_file_name)
                if os.path.isfile(params_file_path):
                    parameters_file = open(params_file_path, "r")
                    my_params = json.load(parameters_file)
                    parameters_file.close()
                    if "RuleSets" in my_params["Parameters"]:
                        s_input = set(self.args.rulesets)
                        s_params = set(my_params["Parameters"]["RuleSets"])
                        if s_input.intersection(s_params):
                            rule_names.append(obj_name)
        elif self.args.rulename:
            for rule_name in self.args.rulename:
                cleaned_rule_name = self.__clean_rule_name(rule_name)
                if os.path.isdir(cleaned_rule_name):
                    rule_names.append(cleaned_rule_name)
        else:
            print('Invalid Option: Specify Rule Name or RuleSet. Run "rdk %s -h" for more info.' % (Command))
            sys.exit(1)

        if len(rule_names) == 0:
            print("No matching rule directories found.")
            sys.exit(1)

        # Check rule names to make sure none are too long.  This is needed to catch Rules created before length constraint was added.
        for name in rule_names:
            if len(name) > 128:
                print(
                    f"Error: Found Rule with name over 128 characters: {name} \n Recreate the Rule with a shorter name."
                )
                sys.exit(1)

        return rule_names

    def __get_rule_parameters(self, rule_name):
        params_file_path = os.path.join(os.getcwd(), rules_dir, rule_name, parameter_file_name)

        try:
            parameters_file = open(params_file_path, "r")
        except IOError as e:
            print(f"Failed to open parameters file for rule '{rule_name}'")
            print(e.message)
            sys.exit(1)

        my_json = {}

        try:
            my_json = json.load(parameters_file)
        except ValueError as ve:  # includes simplejson.decoder.JSONDecodeError
            print(f"Failed to decode JSON in parameters file for Rule {rule_name}")
            print(ve.message)
            parameters_file.close()
            sys.exit(1)
        except Exception as e:
            print(f"Error loading parameters file for Rule {rule_name}")
            print(e.message)
            parameters_file.close()
            sys.exit(1)

        parameters_file.close()

        my_tags = my_json.get("Tags", None)

        # Needed for backwards compatibility with earlier versions of parameters file
        if my_tags is None:
            my_tags = "[]"
            my_json["Parameters"]["Tags"] = my_tags

        # as my_tags was returned as a string in earlier versions, convert it back to a list
        if isinstance(my_tags, str):
            my_tags = json.loads(my_tags)

        return my_json["Parameters"], my_tags

    def __parse_rule_args(self, is_required):
        self.args = get_rule_parser(is_required, self.args.command).parse_args(self.args.command_args, self.args)

        max_resource_types = 100
        if self.args.resource_types and (len(self.args.resource_types.split(",")) > max_resource_types):
            print(f"Number of specified resource types exceeds Config service maximum of {max_resource_types}.")
            sys.exit(1)

        if self.args.excluded_accounts and not re.match(r"^(\d{12})(,\d{12})*$", self.args.excluded_accounts):
            print("Invalid Excluded Accounts. Must be 12-digit account numbers, separated by commas and no spaces.")
            sys.exit(1)

        if self.args.rulename:
            if len(self.args.rulename) > 128:
                print("Rule names must be 128 characters or fewer.")
                sys.exit(1)

        resource_type_error = ""
        if self.args.resource_types:
            for resource_type in self.args.resource_types.split(","):
                if resource_type not in accepted_resource_types:
                    resource_type_error = (
                        resource_type_error + ' "' + resource_type + '" not found in list of accepted resource types.'
                    )
            if resource_type_error:
                print(resource_type_error)
                if not self.args.skip_supported_resource_check:
                    sys.exit(1)
                else:
                    print(
                        "Skip-Supported-Resource-Check Flag set (--skip-supported-resource-check), ignoring missing resource type error."
                    )

        if is_required and not self.args.resource_types and not self.args.maximum_frequency:
            print("You must specify either a resource type trigger or a maximum frequency.")
            sys.exit(1)

        if self.args.input_parameters:
            try:
                print(self.args.input_parameters)
                input_params_dict = json.loads(self.args.input_parameters, strict=False)
            except Exception as e:
                print("Failed to parse input parameters. Remember to escape double-quotes if using Windows.")
                sys.exit(1)

        if self.args.optional_parameters:
            try:
                optional_params_dict = json.loads(self.args.optional_parameters, strict=False)
            except Exception as e:
                print(f"Failed to parse optional parameters. {repr(e)}")
                sys.exit(1)

        if self.args.rulesets:
            self.args.rulesets = self.args.rulesets.split(",")

    def __parse_test_args(self):
        self.args = get_test_parser(self.args.command).parse_args(self.args.command_args, self.args)

        if self.args.all and self.args.rulename:
            print("You may specify either specific rules or --all, but not both.")
            return 1

        if self.args.rulesets:
            self.args.rulesets = self.args.rulesets.split(",")

        return self.args

    def __parse_deploy_args(self, ForceArgument=False):
        self.args = get_deployment_parser(ForceArgument).parse_args(self.args.command_args, self.args)

        # Validate inputs #
        if bool(self.args.lambda_security_groups) != bool(self.args.lambda_subnets):
            print("You must specify both lambda-security-groups and lambda-subnets, or neither.")
            sys.exit(1)

        if self.args.stack_name and not self.args.functions_only:
            print("--stack-name can only be specified when using the --functions-only feature.")
            sys.exit(1)

        # Make sure we're not exceeding Layer limits
        if self.args.lambda_layers:
            layer_count = len(self.args.lambda_layers.split(","))
            if layer_count > 5:
                print("You may only specify 5 Lambda Layers.")
                sys.exit(1)
            if self.args.rdklib_layer_arn or self.args.generated_lambda_layer and layer_count > 4:
                print("Because you have selected a 'lib' runtime You may only specify 4 additional Lambda Layers.")
                sys.exit(1)

        # RDKLib version and RDKLib Layer ARN/Generated RDKLib Layer are mutually exclusive.
        if "rdk_lib_version" in self.args and (self.args.rdklib_layer_arn or self.args.generated_lambda_layer):
            print(
                "Specify EITHER an RDK Lib version to use the official release OR a specific Layer ARN to use a custom implementation."
            )
            sys.exit(1)

        # RDKLib version and RDKLib Layer ARN/Generated RDKLib Layer are mutually exclusive.
        if self.args.rdklib_layer_arn and self.args.generated_lambda_layer:
            print("Specify EITHER an RDK Lib Layer ARN OR the generated lambda layer flag.")
            sys.exit(1)

        # Check rule names to make sure none are too long.  This is needed to catch Rules created before length constraint was added.
        if self.args.rulename:
            for name in self.args.rulename:
                if len(name) > 128:
                    print(
                        f"Error: Found Rule with name over 128 characters: {name} \n Recreate the Rule with a shorter name."
                    )
                    sys.exit(1)

        if self.args.functions_only and not self.args.stack_name:
            self.args.stack_name = "RDK-Config-Rule-Functions"

        if self.args.rulesets:
            self.args.rulesets = self.args.rulesets.split(",")

    def __parse_deploy_organization_args(self, ForceArgument=False):
        self.args = get_deployment_organization_parser(ForceArgument).parse_args(self.args.command_args, self.args)

        # Validate inputs #
        if bool(self.args.lambda_security_groups) != bool(self.args.lambda_subnets):
            print("You must specify both lambda-security-groups and lambda-subnets, or neither.")
            sys.exit(1)

        if self.args.stack_name and not self.args.functions_only:
            print("--stack-name can only be specified when using the --functions-only feature.")
            sys.exit(1)

        # Make sure we're not exceeding Layer limits
        if self.args.lambda_layers:
            layer_count = len(self.args.lambda_layers.split(","))
            if layer_count > 5:
                print("You may only specify 5 Lambda Layers.")
                sys.exit(1)
            if self.args.rdklib_layer_arn and layer_count > 4:
                print("Because you have selected a 'lib' runtime You may only specify 4 additional Lambda Layers.")
                sys.exit(1)

        # RDKLib version and RDKLib Layer ARN are mutually exclusive.
        if "rdk_lib_version" in self.args and "rdklib_layer_arn" in self.args:
            print(
                "Specify EITHER an RDK Lib version to use the official release OR a specific Layer ARN to use a custom implementation."
            )
            sys.exit(1)

        # Check rule names to make sure none are too long.  This is needed to catch Rules created before length constraint was added.
        if self.args.rulename:
            for name in self.args.rulename:
                if len(name) > 128:
                    print(
                        f"Error: Found Rule with name over 128 characters: {name} \n Recreate the Rule with a shorter name."
                    )
                    sys.exit(1)

        if self.args.functions_only and not self.args.stack_name:
            self.args.stack_name = "RDK-Config-Rule-Functions"

        if self.args.rulesets:
            self.args.rulesets = self.args.rulesets.split(",")

        if self.args.excluded_accounts:
            if not re.match(r"^(\d{12})(,\d{12})*$", self.args.excluded_accounts):
                print("Invalid excluded accounts.  Must be a comma-separated list of 12-digit account numbers.")
                sys.exit(1)
            self.args.excluded_accounts = self.args.excluded_accounts.split(",")

    def __parse_export_args(self, ForceArgument=False):
        self.args = get_export_parser(ForceArgument).parse_args(self.args.command_args, self.args)

        if bool(self.args.lambda_security_groups) != bool(self.args.lambda_subnets):
            print("You must specify both lambda-security-groups and lambda-subnets, or neither.")
            sys.exit(1)

        # Check rule names to make sure none are too long.  This is needed to catch Rules created before length constraint was added.
        if self.args.rulename:
            for name in self.args.rulename:
                if len(name) > 128:
                    print(
                        f"Error: Found Rule with name over 128 characters: {name} \n Recreate the Rule with a shorter name."
                    )
                    sys.exit(1)

    def __package_function_code(self, rule_name, params):
        my_session = self.__get_boto_session()
        if params["SourceRuntime"] == "java8":
            # Do java build and package.
            print("Running Gradle Build for " + rule_name)
            working_dir = os.path.join(os.getcwd(), rules_dir, rule_name)
            command = ["gradle", "build"]
            subprocess.call(command, cwd=working_dir)

            # set source as distribution zip
            s3_src = os.path.join(
                os.getcwd(),
                rules_dir,
                rule_name,
                "build",
                "distributions",
                rule_name + ".zip",
            )

        else:
            print("Zipping " + rule_name)
            # Remove old zip file if it already exists
            package_file_dst = os.path.join(rule_name, rule_name + ".zip")
            self.__delete_package_file(package_file_dst)

            # zip rule code files and upload to s3 bucket
            s3_src_dir = os.path.join(os.getcwd(), rules_dir, rule_name)
            tmp_src = shutil.make_archive(
                os.path.join(tempfile.gettempdir(), rule_name + my_session.region_name),
                "zip",
                s3_src_dir,
            )
            if not (os.path.exists(package_file_dst)):
                shutil.copy(tmp_src, package_file_dst)
            s3_src = os.path.abspath(package_file_dst)
            self.__delete_package_file(tmp_src)

        s3_dst = "/".join((rule_name, rule_name + ".zip"))

        print("Zipping complete.")

        return s3_dst

    def __populate_params(self):
        # create custom session based on whatever credentials are available to us
        my_session = self.__get_boto_session()

        # get accountID
        # my_sts = my_session.client('sts')
        # response = my_sts.get_caller_identity()
        # account_id = response['Account']

        my_input_params = {}

        if self.args.input_parameters:
            # Parse the input parameters to make sure it's valid json.  Be tolerant of quote usage in the input string.
            try:
                my_input_params = json.loads(self.args.input_parameters, strict=False)
            except Exception as e:
                print(
                    "Error parsing input parameter JSON.  Make sure your JSON keys and values are enclosed in properly-escaped double quotes and your input-parameters string is enclosed in single quotes."
                )
                raise e

        my_optional_params = {}

        if self.args.optional_parameters:
            # As above, but with the optional input parameters.
            try:
                my_optional_params = json.loads(self.args.optional_parameters, strict=False)
            except Exception as e:
                print(
                    "Error parsing optional input parameter JSON.  Make sure your JSON keys and values are enclosed in properly escaped double quotes and your optional-parameters string is enclosed in single quotes."
                )

        my_tags = []

        if self.args.tags:
            # As above, but with the optional tag key value pairs.
            try:
                my_tags = json.loads(self.args.tags, strict=False)
            except Exception:
                print(
                    "Error parsing optional tags JSON.  Make sure your JSON keys and values are enclosed in properly escaped double quotes and tags string is enclosed in single quotes."
                )

        my_remediation = {}
        if (
            any(
                getattr(self.args, arg) is not None
                for arg in [
                    "auto_remediation_retry_attempts",
                    "auto_remediation_retry_time",
                    "remediation_action_version",
                    "remediation_concurrent_execution_percent",
                    "remediation_error_rate_percent",
                    "remediation_parameters",
                ]
            )
            and not self.args.remediation_action
        ):
            print("Remediation Flags detected but no remediation action (--remediation-action) set")

        if self.args.remediation_action:
            try:
                my_remediation = self.__generate_remediation_params()
            except Exception:
                print("Error parsing remediation configuration.")

        # Get description if provided at command line, or fall back to rulename
        if self.args.description:
            description = self.args.description
        else:
            description = self.args.rulename

        # create config file and place in rule directory
        parameters = {
            "RuleName": self.args.rulename,
            "Description": description,
            "SourceRuntime": self.args.runtime,
            # 'CodeBucket': code_bucket_prefix + account_id,
            "CodeKey": self.args.rulename + my_session.region_name + ".zip",
            "InputParameters": json.dumps(my_input_params),
            "OptionalParameters": json.dumps(my_optional_params),
        }

        if self.args.custom_lambda_name:
            parameters["CustomLambdaName"] = self.args.custom_lambda_name

        tags = json.dumps(my_tags)

        if self.args.resource_types:
            parameters["SourceEvents"] = self.args.resource_types

        if self.args.maximum_frequency:
            parameters["SourcePeriodic"] = self.args.maximum_frequency

        if self.args.rulesets:
            parameters["RuleSets"] = self.args.rulesets

        if self.args.source_identifier:
            parameters["SourceIdentifier"] = self.args.source_identifier
            parameters["CodeKey"] = None
            parameters["SourceRuntime"] = None

        if self.args.excluded_accounts:
            parameters["ExcludedAccounts"] = self.args.excluded_accounts

        if my_remediation:
            parameters["Remediation"] = my_remediation

        self.__write_params_file(self.args.rulename, parameters, tags)

    def __generate_remediation_params(self):
        params = {}
        if self.args.auto_remediate:
            params["Automatic"] = self.args.auto_remediate

        params["ConfigRuleName"] = self.args.rulename

        ssm_controls = {}
        if self.args.remediation_concurrent_execution_percent:
            ssm_controls["ConcurrentExecutionRatePercentage"] = self.args.remediation_concurrent_execution_percent

        if self.args.remediation_error_rate_percent:
            ssm_controls["ErrorPercentage"] = self.args.remediation_error_rate_percent

        if ssm_controls:
            params["ExecutionControls"] = {"SsmControls": ssm_controls}

        if self.args.auto_remediation_retry_attempts:
            params["MaximumAutomaticAttempts"] = self.args.auto_remediation_retry_attempts

        if self.args.remediation_parameters:
            params["Parameters"] = json.loads(self.args.remediation_parameters)

        if self.args.resource_types and len(self.args.resource_types.split(",")) == 1:
            params["ResourceType"] = self.args.resource_types

        if self.args.auto_remediation_retry_time:
            params["RetryAttemptSeconds"] = self.args.auto_remediation_retry_time

        params["TargetId"] = self.args.remediation_action
        params["TargetType"] = "SSM_DOCUMENT"

        if self.args.remediation_action_version:
            params["TargetVersion"] = self.args.remediation_action_version

        return params

    def __write_params_file(self, rulename, parameters, tags):
        my_params = {"Version": "1.0", "Parameters": parameters, "Tags": tags}
        params_file_path = os.path.join(os.getcwd(), rules_dir, rulename, parameter_file_name)
        parameters_file = open(params_file_path, "w")
        json.dump(my_params, parameters_file, indent=2)
        parameters_file.close()

    def __wait_for_cfn_stack(self, cfn_client, stackname):
        my_session = self.__get_boto_session()
        in_progress = True
        while in_progress:
            my_stacks = []
            response = cfn_client.list_stacks()

            all_stacks = response["StackSummaries"]
            while "NextToken" in response:
                response = cfn_client.list_stacks(NextToken=response["NextToken"])
                all_stacks += response["StackSummaries"]

            for stack in all_stacks:
                if stack["StackName"] == stackname:
                    my_stacks.append(stack)

            # Find the stack (if any) that hasn't already been deleted.
            all_deleted = True
            active_stack = None
            for stack in my_stacks:
                if stack["StackStatus"] != "DELETE_COMPLETE":
                    active_stack = stack
                    all_deleted = False

            # If all stacks have been deleted, clearly we're done!
            if all_deleted:
                in_progress = False
                print(f"[{my_session.region_name}]: CloudFormation stack operation complete.")
                continue
            else:
                if "FAILED" in active_stack["StackStatus"]:
                    in_progress = False
                    print(f"[{my_session.region_name}]: CloudFormation stack operation Failed for " + stackname + ".")
                    if "StackStatusReason" in active_stack:
                        print(f"[{my_session.region_name}]: Reason: " + active_stack["StackStatusReason"])
                elif active_stack["StackStatus"] == "ROLLBACK_COMPLETE":
                    in_progress = False
                    print(
                        f"[{my_session.region_name}]: CloudFormation stack operation Rolled Back for " + stackname + "."
                    )
                    if "StackStatusReason" in active_stack:
                        print(f"[{my_session.region_name}]: Reason: " + active_stack["StackStatusReason"])
                elif "COMPLETE" in active_stack["StackStatus"]:
                    in_progress = False
                    print(f"[{my_session.region_name}]: CloudFormation stack operation complete.")
                else:
                    print(f"[{my_session.region_name}]: Waiting for CloudFormation stack operation to complete...")
                    time.sleep(5)

    def __get_handler(self, rule_name, params):
        if "SourceHandler" in params:
            return params["SourceHandler"]
        if params["SourceRuntime"] in [
            "python3.7",
            "python3.7-lib",
            "python3.8",
            "python3.8-lib",
            "python3.9",
            "python3.9-lib",
            "python3.10",
            "python3.10-lib",
            "python3.11",
            "python3.11-lib",
        ]:
            return rule_name + ".lambda_handler"
        elif params["SourceRuntime"] in ["java8"]:
            return "com.rdk.RuleUtil::handler"

    def __get_runtime_string(self, params):
        if params["SourceRuntime"] in [
            "python3.7-lib",
            "python3.8-lib",
            "python3.9-lib",
            "python3.10-lib",
            "python3.11-lib",
        ]:
            runtime = params["SourceRuntime"].split("-")
            return runtime[0]

        return params["SourceRuntime"]

    def __get_test_CIs(self, rulename):
        test_ci_list = []
        if self.args.test_ci_types:
            print("\tTesting with generic CI for supplied Resource Type(s)")
            ci_types = self.args.test_ci_types.split(",")
            for ci_type in ci_types:
                my_test_ci = TestCI(ci_type)
                test_ci_list.append(my_test_ci.get_json())
        else:
            # Check to see if there is a test_ci.json file in the Rule directory
            tests_path = os.path.join(os.getcwd(), rules_dir, rulename, test_ci_filename)
            if os.path.exists(tests_path):
                print("\tTesting with CI's provided in test_ci.json file. NOT YET IMPLEMENTED")  # TODO
            #    test_ci_list self._load_cis_from_file(tests_path)
            else:
                print("\tTesting with generic CI for configured Resource Type(s)")
                my_rule_params, my_rule_tags = self.__get_rule_parameters(rulename)
                ci_types = str(my_rule_params["SourceEvents"]).split(",")
                for ci_type in ci_types:
                    my_test_ci = TestCI(ci_type)
                    test_ci_list.append(my_test_ci.get_json())

        return test_ci_list

    def __get_lambda_arn_for_stack(self, stack_name):
        # create custom session based on whatever credentials are available to us
        my_session = self.__get_boto_session()

        my_cfn = my_session.client("cloudformation")

        # Since CFN won't detect changes to the lambda code stored in S3 as a reason to update the stack,
        # we need to manually update the code reference in Lambda once the CFN has run.
        self.__wait_for_cfn_stack(my_cfn, stack_name)

        # Lambda function is an output of the stack.
        my_updated_stack = my_cfn.describe_stacks(StackName=stack_name)
        cfn_outputs = my_updated_stack["Stacks"][0]["Outputs"]
        my_lambda_arn = "NOTFOUND"
        for output in cfn_outputs:
            if output["OutputKey"] == "RuleCodeLambda":
                my_lambda_arn = output["OutputValue"]

        if my_lambda_arn == "NOTFOUND":
            print(f"[{my_session.region_name}]: Could not read CloudFormation stack output to find Lambda function.")
            sys.exit(1)

        return my_lambda_arn

    def __get_lambda_name(self, rule_name, params):
        if "CustomLambdaName" in params:
            lambda_name = params["CustomLambdaName"]
            if len(lambda_name) > 64:
                print(
                    f"Error: Found Rule's Lambda function with name over 64 characters: {lambda_name}."
                    + "\nRecreate the lambda name with a shorter name."
                )
                sys.exit(1)
            return lambda_name
        else:
            lambda_name = "RDK-Rule-Function-" + self.__get_stack_name_from_rule_name(rule_name)
            if len(lambda_name) > 64:
                print(
                    f"Error: Found Rule's Lambda function with name over 64 characters: {lambda_name}."
                    + "\nRecreate the rule with a shorter name or with CustomLambdaName attribute in parameter.json."
                    + "\nIf you are using 'rdk create', you can add '--custom-lambda-name <your lambda name>' to create your RDK rules"
                )
                sys.exit(1)
            return lambda_name

    def __get_lambda_arn_for_rule(self, rule_name, partition, region, account, params):
        lambda_name = self.__get_lambda_name(rule_name, params)
        return f"arn:{partition}:lambda:{region}:{account}:function:{lambda_name}"

    def __delete_package_file(self, file):
        try:
            os.remove(file)
        except OSError:
            pass

    def __upload_function_code(self, rule_name, params, account_id, my_session, code_bucket_name):
        if params["SourceRuntime"] == "java8":
            # Do java build and package.
            print(f"[{my_session.region_name}]: Running Gradle Build for " + rule_name)
            working_dir = os.path.join(os.getcwd(), rules_dir, rule_name)
            command = ["gradle", "build"]
            subprocess.call(command, cwd=working_dir)

            # set source as distribution zip
            s3_src = os.path.join(
                os.getcwd(),
                rules_dir,
                rule_name,
                "build",
                "distributions",
                rule_name + my_session.region_name + ".zip",
            )
            s3_dst = "/".join((rule_name, rule_name + ".zip"))

            my_s3 = my_session.resource("s3")

            print(f"[{my_session.region_name}]: Uploading " + rule_name)
            my_s3.meta.client.upload_file(s3_src, code_bucket_name, s3_dst)
            print(f"[{my_session.region_name}]: Upload complete.")

        else:
            print(f"[{my_session.region_name}]: Zipping " + rule_name)
            # Remove old zip file if it already exists
            package_file_dst = os.path.join(rule_name, rule_name + ".zip")
            self.__delete_package_file(package_file_dst)

            # zip rule code files and upload to s3 bucket
            s3_src_dir = os.path.join(os.getcwd(), rules_dir, rule_name)

            tmp_src = shutil.make_archive(
                os.path.join(tempfile.gettempdir(), rule_name + my_session.region_name),
                "zip",
                s3_src_dir,
            )

            s3_dst = "/".join((rule_name, rule_name + ".zip"))

            my_s3 = my_session.resource("s3")

            print(f"[{my_session.region_name}]: Uploading " + rule_name)
            my_s3.meta.client.upload_file(tmp_src, code_bucket_name, s3_dst)
            print(f"[{my_session.region_name}]: Upload complete.")
            if not (os.path.exists(package_file_dst)):
                shutil.copy(tmp_src, package_file_dst)
            self.__delete_package_file(tmp_src)

        return s3_dst

    def __create_remediation_cloudformation_block(self, remediation_config):
        remediation = {
            "Type": "AWS::Config::RemediationConfiguration",
            "DependsOn": "rdkConfigRule",
            "Properties": remediation_config,
        }

        return remediation

    def __create_automation_cloudformation_block(self, ssm_automation, rule_name):
        print("Generate SSM Resources")
        ssm_json_dir = os.path.join(os.getcwd(), ssm_automation["Document"])
        print("Reading SSM JSON From -> " + ssm_json_dir)
        # params_file_path = os.path.join(os.getcwd(), rules_dir, rulename, parameter_file_name)
        ssm_automation_content = open(ssm_json_dir, "r").read()
        ssm_automation_json = json.loads(ssm_automation_content)
        ssm_automation_config = {
            "Type": "AWS::SSM::Document",
            "Properties": {
                "DocumentType": "Automation",
                "Content": ssm_automation_json,
            },
        }

        return ssm_automation_config

    def __create_automation_iam_cloudformation_block(self, ssm_automation, rule_name):
        print(
            "Generate IAM Role for SSM Document with these actions",
            str(ssm_automation["IAM"]),
        )

        assume_role_template = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "ssm.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }

        # params_file_path = os.path.join(os.getcwd(), rules_dir, rulename, parameter_file_name)
        ssm_automation_iam_role = {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "Description": "IAM Role to Support Config Remediation for " + rule_name,
                "Path": "/rdk-remediation-role/",
                # "RoleName": {"Fn::Sub": "" + rule_name + "-Remediation-Role-${AWS::Region}"},
                "AssumeRolePolicyDocument": assume_role_template,
            },
        }

        ssm_automation_iam_policy = {
            "Type": "AWS::IAM::Policy",
            "Properties": {
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": ssm_automation["IAM"],
                            "Effect": "Allow",
                            "Resource": "*",
                        }
                    ],
                    "Version": "2012-10-17",
                },
                "PolicyName": {"Fn::Sub": "" + rule_name + "-Remediation-Policy-${AWS::Region}"},
                "Roles": [{"Ref": self.__get_alphanumeric_rule_name(rule_name + "Role")}],
            },
        }

        return (ssm_automation_iam_role, ssm_automation_iam_policy)

    def __create_function_cloudformation_template(self):
        print("Generating CloudFormation template for Lambda Functions!")

        # First add the common elements - description, parameters, and resource section header
        template = {}
        template["AWSTemplateFormatVersion"] = "2010-09-09"
        template[
            "Description"
        ] = "AWS CloudFormation template to create Lambda functions for backing custom AWS Config rules. You will be billed for the AWS resources used if you create a stack from this template."

        parameters = {}
        parameters["SourceBucket"] = {}
        parameters["SourceBucket"]["Description"] = "Name of the S3 bucket that you have stored the rule zip files in."
        parameters["SourceBucket"]["Type"] = "String"
        parameters["SourceBucket"]["MinLength"] = "1"
        parameters["SourceBucket"]["MaxLength"] = "255"

        template["Parameters"] = parameters

        resources = {}

        my_session = self.__get_boto_session()
        identity_details = self.__get_caller_identity_details(my_session)
        account_id = identity_details["account_id"]
        partition = identity_details["partition"]
        lambdaRoleArn = ""
        if self.args.lambda_role_arn:
            print(f"[{my_session.region_name}]: Existing IAM Role provided: " + self.args.lambda_role_arn)
            lambdaRoleArn = self.args.lambda_role_arn
        elif self.args.lambda_role_name:
            print(f"[{my_session.region_name}]: Building IAM Role ARN from Name: " + self.args.lambda_role_name)
            arn = f"arn:{partition}:iam::{account_id}:role/{self.args.lambda_role_name}"
            lambdaRoleArn = arn
        else:
            print("No IAM role provided, creating a new IAM role for lambda function")
            lambda_role = {}
            lambda_role["Type"] = "AWS::IAM::Role"
            lambda_role["Properties"] = {}
            lambda_role["Properties"]["Path"] = "/rdk/"
            lambda_role["Properties"]["AssumeRolePolicyDocument"] = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowLambdaAssumeRole",
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
            lambda_policy_statements = [
                {
                    "Sid": "2",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogStreams",
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                },
                {
                    "Sid": "3",
                    "Action": ["config:PutEvaluations"],
                    "Effect": "Allow",
                    "Resource": "*",
                },
                {
                    "Sid": "4",
                    "Action": ["iam:List*", "iam:Get*"],
                    "Effect": "Allow",
                    "Resource": "*",
                },
                {
                    "Sid": "5",
                    "Action": ["sts:AssumeRole"],
                    "Effect": "Allow",
                    "Resource": "*",
                },
            ]
            if self.args.lambda_subnets and self.args.lambda_security_groups:
                vpc_policy = {
                    "Sid": "LambdaVPCAccessExecution",
                    "Action": [
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DeleteNetworkInterface",
                        "ec2:CreateNetworkInterface",
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                }
                lambda_policy_statements.append(vpc_policy)
            lambda_role["Properties"]["Policies"] = [
                {
                    "PolicyName": "ConfigRulePolicy",
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": lambda_policy_statements,
                    },
                }
            ]
            lambda_role["Properties"]["ManagedPolicyArns"] = [
                {"Fn::Sub": "arn:${AWS::Partition}:iam::aws:policy/ReadOnlyAccess"}
            ]
            resources["rdkLambdaRole"] = lambda_role

        rule_names = self.__get_rule_list_for_command()
        for rule_name in rule_names:
            alphanum_rule_name = self.__get_alphanumeric_rule_name(rule_name)
            params, tags = self.__get_rule_parameters(rule_name)

            if "SourceIdentifier" in params:
                print("Skipping Managed Rule.")
                continue

            lambda_function = {}
            lambda_function["Type"] = "AWS::Lambda::Function"
            properties = {}
            properties["FunctionName"] = self.__get_lambda_name(rule_name, params)
            properties["Code"] = {
                "S3Bucket": {"Ref": "SourceBucket"},
                "S3Key": rule_name + "/" + rule_name + ".zip",
            }
            properties["Description"] = "Function for AWS Config Rule " + rule_name
            properties["Handler"] = self.__get_handler(rule_name, params)
            properties["MemorySize"] = "256"
            if self.args.lambda_role_arn or self.args.lambda_role_name:
                properties["Role"] = lambdaRoleArn
            else:
                lambda_function["DependsOn"] = "rdkLambdaRole"
                properties["Role"] = {"Fn::GetAtt": ["rdkLambdaRole", "Arn"]}
            properties["Runtime"] = self.__get_runtime_string(params)
            properties["Timeout"] = str(self.args.lambda_timeout)
            properties["Tags"] = tags
            if self.args.lambda_subnets and self.args.lambda_security_groups:
                properties["VpcConfig"] = {
                    "SecurityGroupIds": self.args.lambda_security_groups.split(","),
                    "SubnetIds": self.args.lambda_subnets.split(","),
                }
            layers = []
            if self.args.rdklib_layer_arn:
                layers.append(self.args.rdklib_layer_arn)
            if self.args.lambda_layers:
                for layer in self.args.lambda_layers.split(","):
                    layers.append(layer)
            if layers:
                properties["Layers"] = layers

            lambda_function["Properties"] = properties
            resources[alphanum_rule_name + "LambdaFunction"] = lambda_function

            lambda_permissions = {}
            lambda_permissions["Type"] = "AWS::Lambda::Permission"
            lambda_permissions["DependsOn"] = alphanum_rule_name + "LambdaFunction"
            lambda_permissions["Properties"] = {
                "FunctionName": {"Fn::GetAtt": [alphanum_rule_name + "LambdaFunction", "Arn"]},
                "Action": "lambda:InvokeFunction",
                "Principal": "config.amazonaws.com",
            }
            resources[alphanum_rule_name + "LambdaPermissions"] = lambda_permissions

        template["Resources"] = resources

        return json.dumps(template, indent=2)

    def __tag_config_rule(self, rule_name, cfn_tags, my_session):
        config_client = my_session.client("config")
        config_arn = config_client.describe_config_rules(ConfigRuleNames=[rule_name])["ConfigRules"][0]["ConfigRuleArn"]
        response = config_client.tag_resource(ResourceArn=config_arn, Tags=cfn_tags)
        return response

    def __get_lambda_layers(self, my_session, args, params):
        layers = []
        if "SourceRuntime" in params:
            if params["SourceRuntime"] in [
                "python3.7-lib",
                "python3.8-lib",
                "python3.9-lib",
                "python3.10-lib",
                "python3.11-lib",
            ]:
                if hasattr(args, "generated_lambda_layer") and args.generated_lambda_layer:
                    lambda_layer_version = self.__get_existing_lambda_layer(
                        my_session, layer_name=args.custom_layer_name
                    )
                    if not lambda_layer_version:
                        print(
                            f"{my_session.region_name} generated-lambda-layer flag received, but layer [{args.custom_layer_name}] not found in {my_session.region_name}. Creating one now"
                        )
                        self.__create_new_lambda_layer(my_session, layer_name=args.custom_layer_name)
                        lambda_layer_version = self.__get_existing_lambda_layer(
                            my_session, layer_name=args.custom_layer_name
                        )
                    layers.append(lambda_layer_version)
                elif hasattr(args, "rdklib_layer_arn") and args.rdklib_layer_arn:
                    layers.append(args.rdklib_layer_arn)
                else:
                    rdk_lib_version = RDKLIB_LAYER_VERSION[my_session.region_name]
                    rdklib_arn = RDKLIB_ARN_STRING.format(region=my_session.region_name, version=rdk_lib_version)
                    layers.append(rdklib_arn)
        return layers

    def __get_existing_lambda_layer(self, my_session, layer_name="rdklib-layer"):
        region = my_session.region_name
        lambda_client = my_session.client("lambda")
        print(f"[{region}]: Checking for Existing RDK Layer")
        response = lambda_client.list_layer_versions(LayerName=layer_name)
        if response["LayerVersions"]:
            return response["LayerVersions"][0]["LayerVersionArn"]
        elif not response["LayerVersions"]:
            return None

    def __create_new_lambda_layer(self, my_session, layer_name="rdklib-layer"):
        successful_return = None
        if layer_name == "rdklib-layer":
            successful_return = self.__create_new_lambda_layer_serverless_repo(my_session)

        # If that doesn't work, create it locally and upload - SAR doesn't support the custom layer name
        if layer_name != "rdklib-layer" or not successful_return:
            if layer_name == "rdklib-layer":
                print(
                    f"[{my_session.region_name}]: Serverless Application Repository deployment not supported, attempting manual deployment"
                )
            else:
                print(
                    f"[{my_session.region_name}]: Custom name layer not supported with Serverless Application Repository deployment, attempting manual deployment"
                )
            self.__create_new_lambda_layer_locally(my_session, layer_name)

    def __create_new_lambda_layer_serverless_repo(self, my_session):
        try:
            cfn_client = my_session.client("cloudformation")
            sar_client = my_session.client("serverlessrepo")
            sar_client.get_application(ApplicationId=RDKLIB_LAYER_SAR_ID)
            # Try to create the stack from scratch
            create_type = "update"
            try:
                cfn_client.describe_stacks(StackName="serverlessrepo-rdklib")
            except ClientError as ce:
                if ce.response["Error"]["Code"] == "ValidationError":
                    create_type = "create"
                else:
                    raise ce
            change_set_arn = sar_client.create_cloud_formation_change_set(
                ApplicationId=RDKLIB_LAYER_SAR_ID, StackName="rdklib"
            )["ChangeSetId"]
            print(f"[{my_session.region_name}]: Creating change set to deploy rdklib-layer")
            code = self.__check_on_change_set(cfn_client, change_set_arn)
            if code == 1:
                print(
                    f"[{my_session.region_name}]: Lambda layer up to date with the Serverless Application Repository Version"
                )
                return 1
            if code == -1:
                print(f"[{my_session.region_name}]: Error creating change set, attempting to use manual deployment")
                raise ClientError()
            print(f"[{my_session.region_name}]: Executing change set to deploy rdklib-layer")
            cfn_client.execute_change_set(ChangeSetName=change_set_arn)
            waiter = cfn_client.get_waiter(f"stack_{create_type}_complete")
            waiter.wait(StackName="serverlessrepo-rdklib")
            print(f"[{my_session.region_name}]: Successfully executed change set")
            return 1
        # 2021-10-13 -> aws partition regions where SAR is not supported throw EndpointConnectionError and aws-cn throw ClientError
        except (EndpointConnectionError, ClientError):
            return None

    def __create_new_lambda_layer_locally(self, my_session, layer_name="rdklib-layer"):
        region = my_session.region_name
        print(f"[{region}]: Creating new {layer_name}")
        folder_name = "lib" + str(uuid.uuid4())
        shell_command = "pip3 install --target python boto3 botocore rdk rdklib future mock"

        print(f"[{region}]: Installing Packages to {folder_name}/python")
        try:
            os.makedirs(folder_name + "/python")
        except FileExistsError as e:
            print(e)
            sys.exit(1)
        os.chdir(folder_name)
        _ = subprocess.run(shell_command, capture_output=True, shell=True)

        print(f"[{region}]: Creating rdk_lib_layer.zip")
        shutil.make_archive(f"rdk_lib_layer", "zip", ".", "python")
        os.chdir("..")
        s3_client = my_session.client("s3")
        s3_resource = my_session.resource("s3")

        print(f"[{region}]: Creating temporary S3 Bucket")
        bucket_name = "rdkliblayertemp" + str(uuid.uuid4())
        if region != "us-east-1":
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        if region == "us-east-1":
            s3_client.create_bucket(Bucket=bucket_name)

        print(f"[{region}]: Uploading rdk_lib_layer.zip to S3")
        s3_resource.Bucket(bucket_name).upload_file(f"{folder_name}/rdk_lib_layer.zip", layer_name)

        lambda_client = my_session.client("lambda")

        print(f"[{region}]: Publishing Lambda Layer")
        lambda_client.publish_layer_version(
            LayerName=layer_name,
            Content={"S3Bucket": bucket_name, "S3Key": layer_name},
            CompatibleRuntimes=["python3.7", "python3.8", "python3.9", "python3.10", "python3.11"],
        )

        print(f"[{region}]: Deleting temporary S3 Bucket")
        try:
            bucket = s3_resource.Bucket(bucket_name)
            bucket.objects.all().delete()
            bucket.delete()
        except Exception as e:
            print(e)

        print(f"[{region}]: Cleaning up temp_folder")
        shutil.rmtree(f"./{folder_name}")

    def __check_on_change_set(self, cfn_client, name):
        for i in range(0, 120):
            response = cfn_client.describe_change_set(ChangeSetName=name)
            status = response["Status"]
            reason = response.get("StatusReason", "")
            if status == "FAILED" and reason == "No updates are to be performed.":
                return 1
            if status == "CREATE_COMPLETE":
                return 0
            time.sleep(5)
        return -1


class TestCI:
    def __init__(self, ci_type):
        # convert ci_type string to filename format
        ci_file = ci_type.replace("::", "_") + ".json"
        try:
            self.ci_json = json.load(
                open(
                    os.path.join(path.dirname(__file__), "template", example_ci_dir, ci_file),
                    "r",
                )
            )
        except FileNotFoundError:
            resource_url = (
                "https://github.com/awslabs/aws-config-resource-schema/blob/master/config/properties/resource-types/"
            )
            print(
                "No sample CI found for "
                + ci_type
                + ", even though it appears to be a supported CI.  Please log an issue at https://github.com/awslabs/aws-config-rdk."
                + f"\nLook here: {resource_url} for additional info"
            )
            exit(1)

    def get_json(self):
        return self.ci_json
