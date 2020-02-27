#    Copyright 2017-2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
#
#        http://aws.amazon.com/apache2.0/
#
#    or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
from __future__ import print_function
from builtins import input
from past.builtins import basestring
import os
from os import path
import sys
import shutil
import tempfile
import boto3
import json
import time
import imp
import argparse
import botocore
from botocore.exceptions import ClientError
from datetime import datetime
import base64
import ast
import textwrap
import fileinput
import subprocess
from subprocess import call
import fnmatch
import unittest

#sphinx-argparse is a delight.
try:
    from rdk import MY_VERSION
except ImportError:
    MY_VERSION = "<version>"
    pass

try:
    from unittest.mock import MagicMock, patch, ANY
except ImportError:
    import mock
    from mock import MagicMock, patch, ANY

rdk_dir = '.rdk'
rules_dir = ''
tests_dir = ''
util_filename = 'rule_util'
rule_handler = 'rule_code'
rule_template = 'rdk-rule.template'
config_bucket_prefix = 'config-bucket'
config_role_name = 'config-role'
assume_role_policy_file = 'configRuleAssumeRolePolicyDoc.json'
delivery_permission_policy_file = 'deliveryPermissionsPolicy.json'
code_bucket_prefix = 'config-rule-code-bucket-'
parameter_file_name = 'parameters.json'
example_ci_dir = 'example_ci'
test_ci_filename = 'test_ci.json'
event_template_filename = 'test_event_template.json'

RDKLIB_LAYER_VERSION={'ap-southeast-1':'51', 'ap-south-1':'29', 'us-east-2':'31', 'us-east-1':'31', 'us-west-1':'31', 'us-west-2':'30', 'ap-northeast-2':'29', 'ap-southeast-2':'29', 'ap-northeast-1':'29', 'ca-central-1':'29', 'eu-central-1':'29', 'eu-west-1':'29', 'eu-west-2':'29', 'eu-west-3':'29', 'eu-north-1':'29', 'sa-east-1':'29'}
RDKLIB_ARN_STRING = "arn:aws:lambda:{region}:711761543063:layer:rdklib:{version}"

#this need to be update whenever config service supports more resource types : https://docs.aws.amazon.com/config/latest/developerguide/resource-config-reference.html
accepted_resource_types = [
    'AWS::ACM::Certificate', 'AWS::ApiGateway::DomainName', 'AWS::ApiGateway::Method',
    'AWS::ApiGateway::RestApi', 'AWS::ApiGateway::Stage', 'AWS::ApiGatewayV2::Api',
    'AWS::ApiGatewayV2::DomainName', 'AWS::ApiGatewayV2::Stage', 'AWS::AutoScaling::AutoScalingGroup',
    'AWS::AutoScaling::LaunchConfiguration', 'AWS::AutoScaling::ScalingPolicy', 'AWS::AutoScaling::ScheduledAction',
    'AWS::CloudFormation::Stack', 'AWS::CloudFront::Distribution', 'AWS::CloudFront::StreamingDistribution',
    'AWS::CloudTrail::Trail', 'AWS::CloudWatch::Alarm', 'AWS::CodeBuild::Project', 'AWS::CodePipeline::Pipeline',
    'AWS::Config::ResourceCompliance', 'AWS::DynamoDB::Table', 'AWS::EC2::CustomerGateway',
    'AWS::EC2::EgressOnlyInternetGateway', 'AWS::EC2::EIP', 'AWS::EC2::FlowLog',
    'AWS::EC2::Host', 'AWS::EC2::Instance', 'AWS::EC2::InternetGateway', 'AWS::EC2::NatGateway',
    'AWS::EC2::NetworkAcl', 'AWS::EC2::NetworkInterface', 'AWS::EC2::RegisteredHAInstance',
    'AWS::EC2::RouteTable', 'AWS::EC2::SecurityGroup', 'AWS::EC2::Subnet',
    'AWS::EC2::Volume', 'AWS::EC2::VPC', 'AWS::EC2::VPCEndpoint',
    'AWS::EC2::VPCEndpointService', 'AWS::EC2::VPCPeeringConnection',
    'AWS::EC2::VPNConnection', 'AWS::EC2::VPNGateway', 'AWS::ElasticBeanstalk::Application',
    'AWS::ElasticBeanstalk::ApplicationVersion', 'AWS::ElasticBeanstalk::Environment', 'AWS::ElasticLoadBalancing::LoadBalancer',
    'AWS::ElasticLoadBalancingV2::LoadBalancer', 'AWS::Elasticsearch::Domain', 'AWS::IAM::Group',
    'AWS::IAM::Policy', 'AWS::IAM::Role', 'AWS::IAM::User',
    'AWS::KMS::Key', 'AWS::Lambda::Alias', 'AWS::Lambda::Function',
    'AWS::LicenseManager::LicenseConfiguration', 'AWS::MobileHub::Project', 'AWS::QLDB::Ledger',
    'AWS::RDS::DBCluster', 'AWS::RDS::DBClusterParameterGroup', 'AWS::RDS::DBClusterSnapshot',
    'AWS::RDS::DBInstance', 'AWS::RDS::DBOptionGroup', 'AWS::RDS::DBParameterGroup',
    'AWS::RDS::DBSecurityGroup', 'AWS::RDS::DBSnapshot', 'AWS::RDS::DBSubnetGroup',
    'AWS::RDS::EventSubscription', 'AWS::Redshift::Cluster', 'AWS::Redshift::ClusterParameterGroup',
    'AWS::Redshift::ClusterSecurityGroup', 'AWS::Redshift::ClusterSnapshot', 'AWS::Redshift::ClusterSubnetGroup',
    'AWS::Redshift::EventSubscription', 'AWS::S3::AccountPublicAccessBlock', 'AWS::S3::Bucket',
    'AWS::SecretsManager::Secret', 'AWS::ServiceCatalog::CloudFormationProduct', 'AWS::ServiceCatalog::CloudFormationProvisionedProduct',
    'AWS::ServiceCatalog::Portfolio', 'AWS::Shield::Protection', 'AWS::ShieldRegional::Protection',
    'AWS::SNS::Topic', 'AWS::SQS::Queue', 'AWS::SSM::AssociationCompliance',
    'AWS::SSM::ManagedInstanceInventory', 'AWS::SSM::PatchCompliance', 'AWS::WAF::RateBasedRule',
    'AWS::WAF::Rule', 'AWS::WAF::RuleGroup', 'AWS::WAF::WebACL', 'AWS::WAFRegional::RateBasedRule',
    'AWS::WAFRegional::Rule', 'AWS::WAFRegional::RuleGroup', 'AWS::WAFRegional::WebACL',
    'AWS::WAFv2::WebACL', 'AWS::WAFv2::RuleGroup', 'AWS::WAFv2::IPSet',
    'AWS::WAFv2::RegexPatternSet', 'AWS::WAFv2::ManagedRuleSet', 'AWS::XRay::EncryptionConfig'
]

CONFIG_ROLE_ASSUME_ROLE_POLICY_DOCUMENT = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "LOCAL",
                "Effect": "Allow",
                "Principal": {
                    "Service": [
                        "config.amazonaws.com"
                    ]
                },
                "Action": "sts:AssumeRole"
            },
            {
                "Sid": "REMOTE",
                "Effect": "Allow",
                "Principal": {
                    "AWS": {"Fn::Sub": "arn:${AWS::Partition}:iam::${LambdaAccountId}:root"}
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
CONFIG_ROLE_POLICY_DOCUMENT = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "s3:PutObject*",
                "Resource": { "Fn::Sub": "arn:${AWS::Partition}:s3:::${ConfigBucket}/AWSLogs/${AWS::AccountId}/*" },
                "Condition": {
                    "StringLike": {
                        "s3:x-amz-acl": "bucket-owner-full-control"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": "s3:GetBucketAcl",
                "Resource": {"Fn::Sub": "arn:${AWS::Partition}:s3:::${ConfigBucket}"}
            }
        ]
    }

def get_command_parser():
    #This is needed to get sphinx to auto-generate the CLI documentation correctly.
    if '__version__' not in globals() and '__version__' not in locals():
        __version__ = "<version>"

    parser = argparse.ArgumentParser(
        #formatter_class=argparse.RawDescriptionHelpFormatter,
        description='The RDK is a command-line utility for authoring, deploying, and testing custom AWS Config rules.'
        )
    parser.add_argument('-p','--profile', help="[optional] indicate which Profile to use.")
    parser.add_argument('-k','--access-key-id', help="[optional] Access Key ID to use.")
    parser.add_argument('-s','--secret-access-key', help="[optional] Secret Access Key to use.")
    parser.add_argument('-r','--region',help='Select the region to run the command in.')
    #parser.add_argument('--verbose','-v', action='count')
    #Removed for now from command choices: 'test-remote', 'status'
    parser.add_argument('command', metavar='<command>', help='Command to run.  Refer to the usage instructions for each command for more details', choices=['clean', 'create', 'create-rule-template', 'deploy', 'init', 'logs', 'modify', 'rulesets', 'sample-ci', 'test-local', 'undeploy'])
    parser.add_argument('command_args', metavar='<command arguments>', nargs=argparse.REMAINDER, help="Run `rdk <command> --help` to see command-specific arguments.")
    parser.add_argument('-v','--version', help='Display the version of this tool', action="version", version='%(prog)s '+MY_VERSION)

    return parser

def get_init_parser():
    parser = argparse.ArgumentParser(
        prog='rdk init',
        description = 'Sets up AWS Config.  This will enable configuration recording in AWS and ensure necessary S3 buckets and IAM Roles are created.'
    )

    parser.add_argument('--config-bucket-exists-in-another-account', required=False, action='store_true', help='[optional] If the Config bucket exists in another account, remove the check of the bucket')

    return parser

def get_clean_parser():
    parser = argparse.ArgumentParser(
        prog='rdk clean',
        description = 'Removes AWS Config from the account.  This will disable all Config rules and no configuration changes will be recorded!')
    parser.add_argument("--force", required=False, action='store_true', help='[optional] Clean account without prompting for confirmation.')

    return parser

def get_create_parser():
    return get_rule_parser(True, "create")

def get_modify_parser():
    return get_rule_parser(False, "modify")

def get_rule_parser(is_required, command):
    usage_string = "[--runtime <runtime>] [--resource-types <resource types>] [--maximum-frequency <max execution frequency>] [--input-parameters <parameter JSON>] [--tags <tags JSON>] [--rulesets <RuleSet tags>]"

    if is_required:
        usage_string = "--runtime <runtime> [ --resource-types <resource types> | --maximum-frequency <max execution frequency> ] [optional configuration flags] [--rulesets <RuleSet tags>]"

    parser = argparse.ArgumentParser(
        prog='rdk '+command,
        usage="rdk "+command + " <rulename> " + usage_string,
        description="Rules are stored in their own directory along with their metadata.  This command is used to " + command + " the Rule and metadata."
    )
    parser.add_argument('rulename', metavar='<rulename>', help='Rule name to create/modify')
    runtime_group = parser.add_mutually_exclusive_group(required=is_required)
    runtime_group.add_argument('-R','--runtime', required=False, help='Runtime for lambda function', choices=['nodejs4.3', 'java8', 'python2.7', 'python3.6', 'python3.6-lib', 'python3.7', 'dotnetcore1.0', 'dotnetcore2.0'])
    runtime_group.add_argument('--source-identifier', required=False, help="[optional] Used only for creating Managed Rules.")
    parser.add_argument('-r','--resource-types', required=False, help='[optional] Resource types that will trigger event-based Rule evaluation')
    parser.add_argument('-m','--maximum-frequency', required=False, help='[optional] Maximum execution frequency for scheduled Rules', choices=['One_Hour','Three_Hours','Six_Hours','Twelve_Hours','TwentyFour_Hours'])
    parser.add_argument('-i','--input-parameters', help="[optional] JSON for required Config parameters.")
    parser.add_argument('--optional-parameters', help="[optional] JSON for optional Config parameters.")
    parser.add_argument('--tags', help="[optional] JSON for tags to be applied to all CFN created resources.")
    parser.add_argument('-s','--rulesets', required=False, help='[optional] comma-delimited list of RuleSet names to add this Rule to.')
    parser.add_argument('--remediation-action', required=False, help='[optional] SSM document for remediation.')
    parser.add_argument('--remediation-action-version', required=False, help='[optional] SSM document version for remediation action.')
    parser.add_argument('--auto-remediate', action='store_true', required=False, help='[optional] Set the SSM remediation to trigger automatically.')
    parser.add_argument('--auto-remediation-retry-attempts', required=False, help='[optional] Number of times to retry automated remediation.')
    parser.add_argument('--auto-remediation-retry-time', required=False, help='[optional] Duration of automated remediation retries.')
    parser.add_argument('--remediation-concurrent-execution-percent', required=False, help='[optional] Concurrent execution rate of the SSM document for remediation.')
    parser.add_argument('--remediation-error-rate-percent', required=False, help='[optional] Error rate that will mark the batch as "failed" for SSM remediation execution.')
    parser.add_argument('--remediation-parameters', required=False, help='[optional] JSON-formatted string of additional parameters required by the SSM document.')

    return parser

def get_undeploy_parser():
    return get_deployment_parser(ForceArgument=True, Command="undeploy")

def get_deploy_parser():
    return get_deployment_parser()

def get_deployment_parser(ForceArgument=False, Command="deploy"):
    direction = "to"
    if Command=="undeploy":
        direction = "from"

    parser = argparse.ArgumentParser(
        prog='rdk '+Command,
        description="Used to " + Command + " the Config Rule " + direction + " the target account."
    )
    parser.add_argument('rulename', metavar='<rulename>', nargs='*', help='Rule name(s) to deploy.  Rule(s) will be pushed to AWS.')
    parser.add_argument('--all','-a', action='store_true', help="All rules in the working directory will be deployed.")
    parser.add_argument('-s','--rulesets', required=False, help='comma-delimited list of RuleSet names')
    parser.add_argument('-f','--functions-only', action='store_true', required=False, help="[optional] Only deploy Lambda functions.  Useful for cross-account deployments.")
    parser.add_argument('--stack-name', required=False, help="[optional] CloudFormation Stack name for use with --functions-only option.  If omitted, \"RDK-Config-Rule-Functions\" will be used." )
    parser.add_argument('--rdklib-layer-arn', required=False, help="[optional] Lambda Layer ARN that contains the desired rdklib.  Note that Lambda Layers are region-specific.")
    parser.add_argument('--lambda-role-arn', required=False, help="[optional] Assign existing iam role to lambda functions. If omitted, \"rdkLambdaRole\" will be created.")
    parser.add_argument('--lambda-layers', required=False, help="[optional] Comma-separated list of Lambda Layer ARNs to deploy with your Lambda function(s).")
    parser.add_argument('--lambda-subnets', required=False, help="[optional] Comma-separated list of Subnets to deploy your Lambda function(s).")
    parser.add_argument('--lambda-security-groups', required=False, help="[optional] Comma-separated list of Security Groups to deploy with your Lambda function(s).")

    if ForceArgument:
        parser.add_argument("--force", required=False, action='store_true', help='[optional] Remove selected Rules from account without prompting for confirmation.')
    return parser

def get_test_parser(command):
    parser = argparse.ArgumentParser(
        prog='rdk '+command,
        description="Used to run tests on your Config Rule code."
    )
    parser.add_argument('rulename', metavar='<rulename>[,<rulename>,...]', nargs='*', help='Rule name(s) to test')
    parser.add_argument('--all','-a', action='store_true', help="Test will be run against all rules in the working directory.")
    parser.add_argument('--test-ci-json', '-j', help="[optional] JSON for test CI for testing.")
    parser.add_argument('--test-ci-types', '-t', help="[optional] CI type to use for testing.")
    parser.add_argument('--verbose', '-v', action='store_true', help='[optional] Enable full log output')
    parser.add_argument('-s','--rulesets', required=False, help='[p[tional] comma-delimited list of RuleSet names')
    return parser

def get_test_local_parser():
    return get_test_parser("test-local")

def get_sample_ci_parser():
    parser = argparse.ArgumentParser(
        prog='rdk sample-ci',
        description="Provides a way to see sample configuration items for most supported resource types."
    )
    parser.add_argument('ci_type', metavar='<resource type>', help='Resource name (e.g. "AWS::EC2::Instance") to display a sample CI JSON document for.', choices=accepted_resource_types)
    return parser

def get_logs_parser():
    parser = argparse.ArgumentParser(
        prog='rdk logs',
        usage="rdk logs <rulename> [-n/--number NUMBER] [-f/--follow]",
        description="Displays CloudWatch logs for the Lambda Function for the specified Rule."
    )
    parser.add_argument('rulename', metavar='<rulename>', help='Rule whose logs will be displayed')
    parser.add_argument('-f','--follow',  action='store_true', help='[optional] Continuously poll Lambda logs and write to stdout.')
    parser.add_argument('-n','--number',  default=3, help='[optional] Number of previous logged events to display.')
    return parser

def get_rulesets_parser():
    parser = argparse.ArgumentParser(
        prog='rdk rulesets',
        usage="rdk rulesets [list | [ [ add | remove ] <ruleset> <rulename> ]",
        description="Used to describe and manipulate RuleSet tags on Rules."
    )
    parser.add_argument('subcommand', help="One of list, add, or remove")
    parser.add_argument('ruleset', nargs='?', help="Name of RuleSet")
    parser.add_argument('rulename', nargs='?', help="Name of Rule to be added or removed")
    return parser

def get_create_rule_template_parser():
    parser = argparse.ArgumentParser(
        prog='rdk create-rule-template',
        description="Outputs a CloudFormation template that can be used to deploy Config Rules in other AWS Accounts."
    )
    parser.add_argument('rulename', metavar='<rulename>', nargs='*', help='Rule name(s) to include in template.  A CloudFormation template will be created, but Rule(s) will not be pushed to AWS.')
    parser.add_argument('--all','-a', action='store_true', help="All rules in the working directory will be included in the generated CloudFormation template.")
    parser.add_argument('-s','--rulesets', required=False, help='comma-delimited RuleSet names to be included in the generated template.')
    parser.add_argument('-o','--output-file', required=True, default="RDK-Config-Rules", help="filename of generated CloudFormation template")
    parser.add_argument('--config-role-arn', required=False, help="[optional] Assign existing iam role as config role. If omitted, \"config-role\" will be created.")
    parser.add_argument('--rules-only', action="store_true", help="[optional] Generate a CloudFormation Template that only includes the Config Rules and not the Bucket, Configuration Recorder, and Delivery Channel.")
    return parser

class rdk:
    def __init__(self, args):
        self.args = args

    @staticmethod
    def get_command_parser(self):
        return get_command_parser()

    def process_command(self):
        method_to_call = getattr(self, self.args.command.replace('-','_'))
        exit_code = method_to_call()

        return(exit_code)

    def init(self):
        """
            This is a test.
        """
        self.args = get_init_parser().parse_args(self.args.command_args, self.args)
        print ("Running init!")

        #create custom session based on whatever credentials are available to us
        my_session = self.__get_boto_session()

        #Create our ConfigService client
        my_config = my_session.client('config')

        #get accountID, AWS partition (e.g. aws or aws-us-gov), region (us-east-1, us-gov-west-1)
        identity_details = self.__get_caller_identity_details(my_session)
        account_id = identity_details['account_id']
        partition = identity_details['partition']

        config_recorder_exists = False
        config_recorder_name = "default"
        config_role_arn = ""
        delivery_channel_exists = False

        config_bucket_exists = False
        if self.args.config_bucket_exists_in_another_account:
            print("Skipping Config Bucket check due to command line args")
            config_bucket_exists = True

        config_bucket_name = config_bucket_prefix + "-" + account_id

        #Check to see if the ConfigRecorder has been created.
        recorders = my_config.describe_configuration_recorders()
        if len(recorders['ConfigurationRecorders']) > 0:
            config_recorder_exists = True
            config_recorder_name = recorders['ConfigurationRecorders'][0]['name']
            config_role_arn = recorders['ConfigurationRecorders'][0]['roleARN']
            print("Found Config Recorder: " + config_recorder_name)
            print("Found Config Role: " + config_role_arn)

        delivery_channels = my_config.describe_delivery_channels()
        if len(delivery_channels['DeliveryChannels']) > 0:
            delivery_channel_exists = True
            config_bucket_name = delivery_channels['DeliveryChannels'][0]['s3BucketName']

        my_s3 = my_session.client('s3')

        if not config_bucket_exists:
            #check whether bucket exists if not create config bucket
            response = my_s3.list_buckets()
            bucket_exists = False
            for bucket in response['Buckets']:
                if bucket['Name'] == config_bucket_name:
                    print("Found Bucket: " + config_bucket_name)
                    config_bucket_exists = True
                    bucket_exists = True

            if not bucket_exists:
                print('Creating Config bucket '+config_bucket_name )
                if my_session.region_name == 'us-east-1':
                    my_s3.create_bucket(
                        Bucket=config_bucket_name
                    )
                else:
                    my_s3.create_bucket(
                        Bucket=config_bucket_name,
                        CreateBucketConfiguration={
                            'LocationConstraint': my_session.region_name
                        }
                    )

        if not config_role_arn:
            #create config role
            my_iam = my_session.client('iam')
            response = my_iam.list_roles()
            role_exists = False
            for role in response['Roles']:
                if role['RoleName'] == config_role_name:
                    role_exists = True

            if not role_exists:
                print('Creating IAM role config-role')
                assume_role_policy = json.loads(open(os.path.join(path.dirname(__file__), 'template', assume_role_policy_file), 'r').read())
                assume_role_policy['Statement'].append({
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": str(account_id)
                        },
                        "Action": "sts:AssumeRole"
                    })
                my_iam.create_role(RoleName=config_role_name, AssumeRolePolicyDocument=json.dumps(assume_role_policy), Path="/rdk/")

            #attach role policy
            my_iam.attach_role_policy(RoleName=config_role_name, PolicyArn='arn:' + partition + ':iam::aws:policy/service-role/AWSConfigRole')
            my_iam.attach_role_policy(RoleName=config_role_name, PolicyArn='arn:' + partition + ':iam::aws:policy/ReadOnlyAccess')
            policy_template = open(os.path.join(path.dirname(__file__), 'template', delivery_permission_policy_file), 'r').read()
            delivery_permissions_policy = policy_template.replace('ACCOUNTID', account_id)
            my_iam.put_role_policy(RoleName=config_role_name, PolicyName='ConfigDeliveryPermissions', PolicyDocument=delivery_permissions_policy)

            #wait for changes to propagate.
            print('Waiting for IAM role to propagate')
            time.sleep(16)

        #create or update config recorder
        if not config_role_arn:
            config_role_arn = "arn:" + partition + ":iam::" + account_id + ":role/rdk/config-role"

        my_config.put_configuration_recorder(ConfigurationRecorder={'name':config_recorder_name, 'roleARN':config_role_arn, 'recordingGroup':{'allSupported':True, 'includeGlobalResourceTypes': True}})

        if not delivery_channel_exists:
            #create delivery channel
            print("Creating delivery channel to bucket " + config_bucket_name)
            my_config.put_delivery_channel(DeliveryChannel={'name':'default', 's3BucketName':config_bucket_name, 'configSnapshotDeliveryProperties':{'deliveryFrequency':'Six_Hours'}})

        #start config recorder
        my_config.start_configuration_recorder(ConfigurationRecorderName=config_recorder_name)
        print('Config Service is ON')

        print('Config setup complete.')

        #create code bucket
        code_bucket_name = code_bucket_prefix + account_id + "-" + my_session.region_name
        response = my_s3.list_buckets()
        bucket_exists = False
        for bucket in response['Buckets']:
            if bucket['Name'] == code_bucket_name:
                bucket_exists = True
                print ("Found code bucket: " + code_bucket_name)

        if not bucket_exists:
            print('Creating Code bucket '+code_bucket_name )

            bucket_configuration = {}

            #Consideration for us-east-1 S3 API
            if my_session.region_name == 'us-east-1':
                my_s3.create_bucket(
                    Bucket=code_bucket_name
                )
            else:
                my_s3.create_bucket(
                    Bucket=code_bucket_name,
                    CreateBucketConfiguration={
                        'LocationConstraint': my_session.region_name
                    }
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

        print ("Running clean!")

        #create custom session based on whatever credentials are available to us
        my_session = self.__get_boto_session()

        #Create our ConfigService client
        my_config = my_session.client('config')

        #Create an S3 client for various things.
        s3_client = my_session.client('s3')

        #Create an IAM client!  Create all the clients!
        iam_client = my_session.client('iam')
        cfn_client = my_session.client('cloudformation')

        #get accountID
        identity_details = self.__get_caller_identity_details(my_session)
        account_id = identity_details['account_id']

        config_recorder_name = ""
        config_role_arn = ""
        delivery_channel_exists = False
        config_bucket_name = ""

        recorders = my_config.describe_configuration_recorders()
        if len(recorders['ConfigurationRecorders']) > 0:
            config_role_arn = recorders['ConfigurationRecorders'][0]['roleARN']
            try:
                #First delete the Config Recorder itself.  Do we need to stop it first?  Let's stop it just to be safe.
                my_config.stop_configuration_recorder(ConfigurationRecorderName=recorders['ConfigurationRecorders'][0]["name"])
                my_config.delete_configuration_recorder(ConfigurationRecorderName=recorders['ConfigurationRecorders'][0]["name"])
            except Exception as e:
                print("Error encountered removing Configuration Recorder: " + str(e))

        #Once the config recorder has been deleted there should be no dependencies on the Config Role anymore.

        try:
            response = iam_client.get_role(RoleName=config_role_name)
            try:
                role_policy_results = iam_client.list_role_policies(RoleName=config_role_name)
                for policy_name in role_policy_results['PolicyNames']:
                    iam_client.delete_role_policy(
                        RoleName=config_role_name,
                        PolicyName=policy_name
                    )

                role_policy_results = iam_client.list_attached_role_policies(RoleName=config_role_name)
                for policy in role_policy_results["AttachedPolicies"]:
                    iam_client.detach_role_policy(
                        RoleName=config_role_name,
                        PolicyArn=policy["PolicyArn"]
                    )

                #Once all policies are detached we should be able to delete the Role.
                iam_client.delete_role(
                    RoleName=config_role_name
                )
            except Exception as e:
                print("Error encountered removing Config Role: " + str(e))
        except Exception as e2:
            print("Error encountered finding Config Role to remove: " + str(e2))

        config_bucket_names = []
        delivery_channels = my_config.describe_delivery_channels()
        if len(delivery_channels['DeliveryChannels']) > 0:
            for delivery_channel in delivery_channels['DeliveryChannels']:
                config_bucket_names.append(delivery_channels['DeliveryChannels'][0]['s3BucketName'])
                try:
                    my_config.delete_delivery_channel(
                        DeliveryChannelName=delivery_channel['name']
                    )
                except Exception as e:
                    print("Error encountered trying to delete Delivery Channel: " + str(e))

        if config_bucket_names:
            #empty and then delete the config bucket.
            for config_bucket_name in config_bucket_names:
                try:
                    config_bucket = my_session.resource("s3").Bucket(config_bucket_name)
                    config_bucket.objects.all().delete()
                    config_bucket.delete()
                except Exception as e:
                    print("Error encountered trying to delete config bucket: " + str(e))

        #Delete any of the Rules deployed the traditional way.
        self.args.all = True
        rule_names = self.__get_rule_list_for_command()
        for rule_name in rule_names:
            my_stack_name = self.__get_stack_name_from_rule_name(rule_name)
            try:
                cfn_client.delete_stack(StackName=my_stack_name)
            except Exception as e:
                print("Error encountered deleting Rule stack: " + str(e))

        #Delete the Functions stack, if one exists.
        try:
            response = cfn_client.describe_stacks(StackName="RDK-Config-Rule-Functions")
            if response["Stacks"]:
                cfn_client.delete_stack(StackName="RDK-Config-Rule-Functions")
        except ClientError as ce:
            if ce.response['Error']['Code'] == "ValidationError":
                print("No Functions stack found.")
        except Exception as e:
            print("Error encountered deleting Functions stack: " + str(e))

        #Delete the code bucket, if one exists.
        code_bucket_name = code_bucket_prefix + account_id + "-" + my_session.region_name
        try:
            code_bucket = my_session.resource("s3").Bucket(code_bucket_name)
            code_bucket.objects.all().delete()
            code_bucket.delete()
        except ClientError as ce:
            if ce.response['Error']['Code'] == "NoSuchBucket":
                print("No code bucket found.")
        except Exception as e:
            print("Error encountered trying to delete code bucket: " + str(e))

        #Done!
        print("Config has been removed.")

    def create(self):
        #Parse the command-line arguments relevant for creating a Config Rule.
        self.__parse_rule_args(True)

        print ("Running create!")

        if not self.args.source_identifier:
            if not self.args.runtime:
                print("Runtime is required for 'create' command.")
                return 1

            extension_mapping = {
                'java8': '.java',
                'python2.7': '.py',
                'python3.6': '.py',
                'python3.6-managed':'.py',
                'python3.6-lib':'.py',
                'python3.7': '.py',
                'nodejs4.3': '.js',
                'dotnetcore1.0': 'cs',
                'dotnetcore2.0': 'cs',
                'python3.6-managed': '.py',
            }
            if self.args.runtime not in extension_mapping:
                print ("rdk does not support that runtime yet.")

        #if not self.args.maximum_frequency:
        #    self.args.maximum_frequency = "TwentyFour_Hours"
        #    print("Defaulting to TwentyFour_Hours Maximum Frequency.")

        #create rule directory.
        rule_path = os.path.join(os.getcwd(), rules_dir, self.args.rulename)
        if os.path.exists(rule_path):
            print("Local Rule directory already exists.")
            return 1

        try:
            os.makedirs(os.path.join(os.getcwd(), rules_dir, self.args.rulename))

            if not self.args.source_identifier:
                #copy rule template into rule directory
                if self.args.runtime == 'java8':
                    self.__create_java_rule()
                elif self.args.runtime in ['dotnetcore1.0', 'dotnetcore2.0']:
                    self.__create_dotnet_rule()
                else:
                    src = os.path.join(path.dirname(__file__), 'template', 'runtime', self.args.runtime, rule_handler + extension_mapping[self.args.runtime])
                    dst = os.path.join(os.getcwd(), rules_dir, self.args.rulename, self.args.rulename + extension_mapping[self.args.runtime])
                    shutil.copyfile(src, dst)
                    f = fileinput.input(files=dst, inplace=True)
                    for line in f:
                        print(line.replace('<%RuleName%>', self.args.rulename), end='')
                    f.close()

                    src = os.path.join(path.dirname(__file__), 'template', 'runtime', self.args.runtime, 'rule_test' + extension_mapping[self.args.runtime])
                    if os.path.exists(src):
                        dst = os.path.join(os.getcwd(), rules_dir, self.args.rulename, self.args.rulename+"_test"+extension_mapping[self.args.runtime])
                        shutil.copyfile(src, dst)
                        #with fileinput.FileInput(dst, inplace=True) as file:
                        f = fileinput.input(files=dst, inplace=True)
                        for line in f:
                            print(line.replace('<%RuleName%>', self.args.rulename), end='')
                        f.close()

                    src = os.path.join(path.dirname(__file__), 'template', 'runtime', self.args.runtime, util_filename + extension_mapping[self.args.runtime])
                    if os.path.exists(src):
                        dst = os.path.join(os.getcwd(), rules_dir, self.args.rulename, util_filename + extension_mapping[self.args.runtime])
                        shutil.copyfile(src, dst)

            #Write the parameters to a file in the rule directory.
            self.__populate_params()

            print ("Local Rule files created.")
        except Exception as e:
            print("Error during create: " + str(e))
            print("Rolling back...")

            shutil.rmtree(rule_path)

            raise e
        return 0

    def modify(self):
        #Parse the command-line arguments necessary for modifying a Config Rule.
        self.__parse_rule_args(False)

        print("Running modify!")

        self.args.rulename = self.__clean_rule_name(self.args.rulename)

        #Get existing parameters
        old_params, tags = self.__get_rule_parameters(self.args.rulename)

        if not self.args.resource_types and 'SourceEvents' in old_params:
            self.args.resource_types = old_params['SourceEvents']

        if not self.args.maximum_frequency and 'SourcePeriodic' in old_params:
            self.args.maximum_frequency = old_params['SourcePeriodic']

        if not self.args.runtime and old_params['SourceRuntime']:
            self.args.runtime = old_params['SourceRuntime']

        if not self.args.input_parameters and 'InputParameters' in old_params:
            self.args.input_parameters = old_params['InputParameters']

        if not self.args.optional_parameters and 'OptionalParameters' in old_params:
            self.args.optional_parameters = old_params['OptionalParameters']

        if not self.args.source_identifier and 'SourceIdentifier' in old_params:
            self.args.source_identifier = old_params['SourceIdentifier']

        if not self.args.tags and tags:
            self.args.tags = tags

        if not self.args.remediation_action and 'Remediation' in old_params:
            params = old_params["Remediation"]
            self.args.auto_remediate = params.get("Automatic", "")
            execution_controls = params.get("ExecutionControls", "")
            if execution_controls:
                ssm_controls = execution_controls["SsmControls"]
                self.args.remediation_concurrent_execution_percent = ssm_controls.get("ConcurrentExecutionRatePercentage", "")
                self.args.remediation_error_rate_percent = ssm_controls.get("ErrorPercentage", "")
            self.args.remediation_parameters = json.dumps(params["Parameters"]) if params.get("Parameters") else None
            self.args.auto_remediation_retry_attempts = params.get("MaximumAutomaticAttempts", "")
            self.args.auto_remediation_retry_time = params.get("RetryAttemptSeconds", "")
            self.args.remediation_action = params.get("TargetId", "")
            self.args.remediation_action_version = params.get("TargetVersion", "")

        if 'RuleSets' in old_params:
            if not self.args.rulesets:
                self.args.rulesets = old_params['RuleSets']

        #Write the parameters to a file in the rule directory.
        self.__populate_params()

        print ("Modified Rule '"+self.args.rulename+"'.  Use the `deploy` command to push your changes to AWS.")

    def undeploy(self):
        self.__parse_deploy_args(ForceArgument=True)

        if not self.args.force:
            confirmation = False
            while not confirmation:
                my_input = input("Delete specified Rules and Lamdba Functions from your AWS Account? (y/N): ")
                if my_input.lower() == "y":
                    confirmation = True
                if my_input.lower() == "n" or my_input == "":
                    sys.exit(0)

        #get the rule names
        rule_names = self.__get_rule_list_for_command()

        print("Running un-deploy!")

        #create custom session based on whatever credentials are available to us.
        my_session = self.__get_boto_session()

        #Collect a list of all of the CloudFormation templates that we delete.  We'll need it at the end to make sure everything worked.
        deleted_stacks = []

        cfn_client = my_session.client('cloudformation')

        if self.args.functions_only:
            try:
                cfn_client.delete_stack(StackName=self.args.stack_name)
                deleted_stacks.append(self.args.stack_name)
            except ClientError as ce:
                print("Client Error encountered attempting to delete CloudFormation stack for Lambda Functions: " + str(ce))
            except Exception as e:
                print("Exception encountered attempting to delete CloudFormation stack for Lambda Functions: " + str(e))

            return

        for rule_name in rule_names:
            try:
                cfn_client.delete_stack(StackName=self.__get_stack_name_from_rule_name(rule_name))
                deleted_stacks.append(self.__get_stack_name_from_rule_name(rule_name))
            except ClientError as ce:
                print("Client Error encountered attempting to delete CloudFormation stack for Rule: " + str(ce))
            except Exception as e:
                print("Exception encountered attempting to delete CloudFormation stack for Rule: " + str(e))

        print("Rule removal initiated. Waiting for Stack Deletion to complete.")

        for stack_name in deleted_stacks:
            self.__wait_for_cfn_stack(cfn_client, stack_name)

        print("Rule removal complete, but local files have been preserved.")
        print("To re-deploy, use the 'deploy' command.")

    def deploy(self):
        self.__parse_deploy_args()

        #get the rule names
        rule_names = self.__get_rule_list_for_command()

        #run the deploy code
        print ("Running deploy!")

        #create custom session based on whatever credentials are available to us
        my_session = self.__get_boto_session()

        #get accountID
        identity_details = self.__get_caller_identity_details(my_session)
        account_id = identity_details['account_id']
        partition = identity_details['partition']

        code_bucket_name = code_bucket_prefix + account_id + "-" + my_session.region_name

        #If we're only deploying the Lambda functions (and role + permissions), branch here.  Someday the "main" execution path should use the same generated CFN templates for single-account deployment.
        if self.args.functions_only:
            #Generate the template
            function_template = self.__create_function_cloudformation_template()

            #Generate CFN parameter json
            cfn_params = [
                {
                    'ParameterKey': 'SourceBucket',
                    'ParameterValue': code_bucket_name,
                }
            ]

            #Write template to S3
            my_s3_client = my_session.client('s3')
            my_s3_client.put_object(
                Body=bytes(function_template.encode('utf-8')),
                Bucket=code_bucket_name,
                Key=self.args.stack_name + ".json"
            )

            #Package code and push to S3
            s3_code_objects = {}
            for rule_name in rule_names:
                rule_params, cfn_tags = self.__get_rule_parameters(rule_name)
                if 'SourceIdentifier' in rule_params:
                    print("Skipping code packaging for Managed Rule.")
                else:
                    s3_dst = self.__upload_function_code(rule_name, rule_params, account_id, my_session, code_bucket_name)
                    s3_code_objects[rule_name] = s3_dst

            my_cfn = my_session.client('cloudformation')

            # Generate the template_url regardless of region using the s3 sdk
            config = my_s3_client._client_config
            config.signature_version = botocore.UNSIGNED
            template_url = boto3.client('s3', config=config).generate_presigned_url('get_object', ExpiresIn=0, Params={'Bucket': code_bucket_name, 'Key': self.args.stack_name + ".json"})

            # Check if stack exists.  If it does, update it.  If it doesn't, create it.

            try:
                my_stack = my_cfn.describe_stacks(StackName=self.args.stack_name)

                #If we've gotten here, stack exists and we should update it.
                print ("Updating CloudFormation Stack for Lambda functions.")
                try:

                    cfn_args = {
                        'StackName': self.args.stack_name,
                        'TemplateURL': template_url,
                        'Parameters': cfn_params,
                        'Capabilities': [ 'CAPABILITY_IAM' ]
                    }

                    # If no tags key is specified, or if the tags dict is empty
                    if cfn_tags is not None:
                        cfn_args['Tags'] = cfn_tags

                    response = my_cfn.update_stack(**cfn_args)

                    #wait for changes to propagate.
                    self.__wait_for_cfn_stack(my_cfn, self.args.stack_name)
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ValidationError':
                        if 'No updates are to be performed.' in str(e):
                            #No changes made to Config rule definition, so CloudFormation won't do anything.
                            print("No changes to Config Rule configurations.")
                        else:
                            #Something unexpected has gone wrong.  Emit an error and bail.
                            print(e)
                            return 1
                    else:
                        raise

                #Push lambda code to functions.
                for rule_name in rule_names:
                    my_lambda_arn = self.__get_lambda_arn_for_rule(rule_name, partition, my_session.region_name, account_id)
                    rule_params, cfn_tags = self.__get_rule_parameters(rule_name)
                    if 'SourceIdentifier' in rule_params:
                        print("Skipping Lambda upload for Managed Rule.")
                        continue

                    print("Publishing Lambda code...")
                    my_lambda_client = my_session.client('lambda')
                    my_lambda_client.update_function_code(
                        FunctionName=my_lambda_arn,
                        S3Bucket=code_bucket_name,
                        S3Key=s3_code_objects[rule_name],
                        Publish=True
                    )
                    print("Lambda code updated.")
            except ClientError as e:
                #If we're in the exception, the stack does not exist and we should create it.
                print ("Creating CloudFormation Stack for Lambda Functions.")

                cfn_args = {
                    'StackName': self.args.stack_name,
                    'TemplateURL': template_url,
                    'Parameters': cfn_params,
                    'Capabilities': ['CAPABILITY_IAM']
                }

                # If no tags key is specified, or if the tags dict is empty
                if cfn_tags is not None:
                    cfn_args['Tags'] = cfn_tags

                response = my_cfn.create_stack(**cfn_args)

                #wait for changes to propagate.
                self.__wait_for_cfn_stack(my_cfn, self.args.stack_name)

            #We're done!  Return with great success.
            sys.exit(0)

        #If we're deploying both the functions and the Config rules, run the following process:
        for rule_name in rule_names:
            rule_params, cfn_tags = self.__get_rule_parameters(rule_name)

            #create CFN Parameters common for Managed and Custom
            source_events = "NONE"
            if 'SourceEvents' in rule_params:
                source_events = rule_params['SourceEvents']

            source_periodic = "NONE"
            if 'SourcePeriodic' in rule_params:
                source_periodic = rule_params['SourcePeriodic']

            combined_input_parameters = {}
            if 'InputParameters' in rule_params:
                combined_input_parameters.update(json.loads(rule_params['InputParameters']))

            if 'OptionalParameters' in rule_params:
                #Remove empty parameters
                keys_to_delete = []
                optional_parameters_json = json.loads(rule_params['OptionalParameters'])
                for key, value in optional_parameters_json.items():
                    if not value:
                        keys_to_delete.append(key)
                for key in keys_to_delete:
                    del optional_parameters_json[key]
                combined_input_parameters.update(optional_parameters_json)

            if 'SourceIdentifier' in rule_params:
                print("Found Managed Rule.")
                #create CFN Parameters for Managed Rules

                my_params = [
                    {
                        'ParameterKey': 'RuleName',
                        'ParameterValue': rule_name,
                    },
                    {
                        'ParameterKey': 'SourceEvents',
                        'ParameterValue': source_events,
                    },
                    {
                        'ParameterKey': 'SourcePeriodic',
                        'ParameterValue': source_periodic,
                    },
                    {
                        'ParameterKey': 'SourceInputParameters',
                        'ParameterValue': json.dumps(combined_input_parameters),
                    },
                    {
                        'ParameterKey': 'SourceIdentifier',
                        'ParameterValue': rule_params['SourceIdentifier']
                    }]
                
                my_cfn = my_session.client('cloudformation')
                #Check if this managed rule needs to have an assoicated remedation block
                remediation = ""
                if "Remediation" in rule_params:
                    print('Build The CFN Template with Remediation Settings')
                    cfn_body = os.path.join(path.dirname(__file__), 'template',  "configManagedRuleWithRemediation.json")
                    template_body = open(cfn_body, "r").read()
                    json_body = json.loads(template_body)
                    remediation = self.__create_remediation_cloudformation_block(rule_params["Remediation"])
                    json_body["Resources"]["Remediation"] = remediation
                    
                    try:
                        my_stack_name = self.__get_stack_name_from_rule_name(rule_name)
                        my_stack = my_cfn.describe_stacks(StackName=my_stack_name)
                        #If we've gotten here, stack exists and we should update it.
                        print ("Updating CloudFormation Stack for " + rule_name)
                        try:
                            cfn_args = {
                                'StackName': my_stack_name,
                                'TemplateBody': json.dumps(json_body),
                                'Parameters': my_params
                            }

                            # If no tags key is specified, or if the tags dict is empty
                            if cfn_tags is not None:
                                cfn_args['Tags'] = cfn_tags

                            response = my_cfn.update_stack(**cfn_args)
                        except ClientError as e:
                            if e.response['Error']['Code'] == 'ValidationError':
                                if 'No updates are to be performed.' in str(e):
                                    #No changes made to Config rule definition, so CloudFormation won't do anything.
                                    print("No changes to Config Rule.")
                                else:
                                    #Something unexpected has gone wrong.  Emit an error and bail.
                                    print(e)
                                    return 1
                            else:
                                raise
                    except ClientError as e:
                        #If we're in the exception, the stack does not exist and we should create it.
                        print ("Creating CloudFormation Stack for " + rule_name)
                        
                        if "Remediation" in rule_params:
                            cfn_args = {
                                'StackName': my_stack_name,
                                'TemplateBody': json.dumps(json_body),
                                'Parameters': my_params
                            }


                        else:
                            cfn_args = {
                                'StackName': my_stack_name,
                                'TemplateBody': open(cfn_body, "r").read(),
                                'Parameters': my_params
                            }

                        if cfn_tags is not None:
                            cfn_args['Tags'] = cfn_tags

                        response = my_cfn.create_stack(**cfn_args)

                    #wait for changes to propagate.
                    self.__wait_for_cfn_stack(my_cfn, my_stack_name)

                    continue


                    

                else:
                #deploy config rule
                    cfn_body = os.path.join(path.dirname(__file__), 'template',  "configManagedRule.json")

                    try:
                        my_stack_name = self.__get_stack_name_from_rule_name(rule_name)
                        my_stack = my_cfn.describe_stacks(StackName=my_stack_name)
                        #If we've gotten here, stack exists and we should update it.
                        print ("Updating CloudFormation Stack for " + rule_name)
                        try:
                            cfn_args = {
                                'StackName': my_stack_name,
                                'TemplateBody': open(cfn_body, "r").read(),
                                'Parameters': my_params
                            }

                            # If no tags key is specified, or if the tags dict is empty
                            if cfn_tags is not None:
                                cfn_args['Tags'] = cfn_tags

                            response = my_cfn.update_stack(**cfn_args)
                        except ClientError as e:
                            if e.response['Error']['Code'] == 'ValidationError':
                                if 'No updates are to be performed.' in str(e):
                                    #No changes made to Config rule definition, so CloudFormation won't do anything.
                                    print("No changes to Config Rule.")
                                else:
                                    #Something unexpected has gone wrong.  Emit an error and bail.
                                    print(e)
                                    return 1
                            else:
                                raise
                    except ClientError as e:
                        #If we're in the exception, the stack does not exist and we should create it.
                        print ("Creating CloudFormation Stack for " + rule_name)
                        cfn_args = {
                            'StackName': my_stack_name,
                            'TemplateBody': open(cfn_body, "r").read(),
                            'Parameters': my_params
                        }

                        if cfn_tags is not None:
                            cfn_args['Tags'] = cfn_tags

                        response = my_cfn.create_stack(**cfn_args)

                    #wait for changes to propagate.
                    self.__wait_for_cfn_stack(my_cfn, my_stack_name)

                    continue

            print("Found Custom Rule.")

            s3_src = ""
            s3_dst = self.__upload_function_code(rule_name, rule_params, account_id, my_session, code_bucket_name)

            #create CFN Parameters for Custom Rules
            lambdaRoleArn = ""
            if self.args.lambda_role_arn:
                print ("Existing IAM Role provided: " + self.args.lambda_role_arn)
                lambdaRoleArn = self.args.lambda_role_arn

            my_params = [
                {
                    'ParameterKey': 'RuleName',
                    'ParameterValue': rule_name,
                },
                {
                    'ParameterKey': 'LambdaRoleArn',
                    'ParameterValue': lambdaRoleArn,
                },
                {
                    'ParameterKey': 'SourceBucket',
                    'ParameterValue': code_bucket_name,
                },
                {
                    'ParameterKey': 'SourcePath',
                    'ParameterValue': s3_dst,
                },
                {
                    'ParameterKey': 'SourceRuntime',
                    'ParameterValue': self.__get_runtime_string(rule_params),
                },
                {
                    'ParameterKey': 'SourceEvents',
                    'ParameterValue': source_events,
                },
                {
                    'ParameterKey': 'SourcePeriodic',
                    'ParameterValue': source_periodic,
                },
                {
                    'ParameterKey': 'SourceInputParameters',
                    'ParameterValue': json.dumps(combined_input_parameters),
                },
                {
                    'ParameterKey': 'SourceHandler',
                    'ParameterValue': self.__get_handler(rule_name, rule_params)

                }]
            layers = []
            rdk_lib_version = "0"
            if 'SourceRuntime' in rule_params:
                if rule_params['SourceRuntime'] == "python3.6-lib":
                    if self.args.rdklib_layer_arn:
                        layers.append(self.args.rdklib_layer_arn)
                    else:
                        rdk_lib_version = RDKLIB_LAYER_VERSION[my_session.region_name]
                        rdklib_arn = RDKLIB_ARN_STRING.format(region=my_session.region_name, version=rdk_lib_version)
                        layers.append(rdklib_arn)


            if self.args.lambda_layers:
                additional_layers = self.args.lambda_layers.split(',')
                layers.extend(additional_layers)

            if layers:
                my_params.append({
                    'ParameterKey': 'Layers',
                    'ParameterValue': ",".join(layers)
                })

            if self.args.lambda_security_groups and self.args.lambda_subnets:
                my_params.append({
                    'ParameterKey': 'SecurityGroupIds',
                    'ParameterValue': self.args.lambda_security_groups
                },{
                    'ParameterKey': 'SubnetIds',
                    'ParameterValue': self.args.lambda_subnets
                })

            #create json of CFN template
            cfn_body = os.path.join(path.dirname(__file__), 'template',  "configRule.json")
            template_body = open(cfn_body, "r").read()
            json_body = json.loads(template_body)

            remediation = ""
            if "Remediation" in rule_params:
                remediation = self.__create_remediation_cloudformation_block(rule_params["Remediation"])
                json_body["Resources"]["Remediation"] = remediation

            #debugging
            #print(json.dumps(json_body, indent=2))

            #deploy config rule
            my_cfn = my_session.client('cloudformation')
            try:
                my_stack_name = self.__get_stack_name_from_rule_name(rule_name)
                my_stack = my_cfn.describe_stacks(StackName=my_stack_name)
                #If we've gotten here, stack exists and we should update it.
                print ("Updating CloudFormation Stack for " + rule_name)
                try:
                    cfn_args = {
                        'StackName': my_stack_name,
                        'TemplateBody': json.dumps(json_body),
                        'Parameters': my_params,
                        'Capabilities': ['CAPABILITY_IAM']
                    }

                    # If no tags key is specified, or if the tags dict is empty
                    if cfn_tags is not None:
                        cfn_args['Tags'] = cfn_tags

                    response = my_cfn.update_stack(**cfn_args)
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ValidationError':
                        if 'No updates are to be performed.' in str(e):
                            #No changes made to Config rule definition, so CloudFormation won't do anything.
                            print("No changes to Config Rule.")
                        else:
                            #Something unexpected has gone wrong.  Emit an error and bail.
                            print(e)
                            return 1
                    else:
                        raise

                my_lambda_arn = self.__get_lambda_arn_for_stack(my_stack_name)

                print("Publishing Lambda code...")
                my_lambda_client = my_session.client('lambda')
                my_lambda_client.update_function_code(
                    FunctionName=my_lambda_arn,
                    S3Bucket=code_bucket_name,
                    S3Key=s3_dst,
                    Publish=True
                )
                print("Lambda code updated.")
            except ClientError as e:
                #If we're in the exception, the stack does not exist and we should create it.
                print ("Creating CloudFormation Stack for " + rule_name)
                cfn_args = {
                    'StackName': my_stack_name,
                    'TemplateBody': json.dumps(json_body),
                    'Parameters': my_params,
                    'Capabilities': ['CAPABILITY_IAM']
                }

                if cfn_tags is not None:
                    cfn_args['Tags'] = cfn_tags

                response = my_cfn.create_stack(**cfn_args)

            #wait for changes to propagate.
            self.__wait_for_cfn_stack(my_cfn, my_stack_name)

        print('Config deploy complete.')

        return 0

    def test_local(self):
        print ("Running local test!")
        tests_successful = True

        args = self.__parse_test_args()

        #Construct our list of rules to test.
        rule_names = self.__get_rule_list_for_command()

        for rule_name in rule_names:
            rule_params, rule_tags = self.__get_rule_parameters(rule_name)
            if rule_params['SourceRuntime'] not in ('python2.7', 'python3.6', 'python3.6-lib', 'python3.7'):
                print ("Skipping " + rule_name + " - Runtime not supported for local testing.")
                continue

            print("Testing "+rule_name)
            test_dir = os.path.join(os.getcwd(), rules_dir, rule_name)
            print("Looking for tests in " + test_dir)

            if args.verbose == True:
                results = unittest.TextTestRunner(buffer=False, verbosity=2).run(self.__create_test_suite(test_dir))
            else:
                results = unittest.TextTestRunner(buffer=True, verbosity=2).run(self.__create_test_suite(test_dir))

            print (results)

            tests_successful = tests_successful and results.wasSuccessful()
        return int(not tests_successful)

    def test_remote(self):
        print ("Running test_remote!")
        self.__parse_test_args()

        #Construct our list of rules to test.
        rule_names = self.__get_rule_list_for_command()

        #Create our Lambda client.
        my_session = self.__get_boto_session()
        my_lambda_client = my_session.client('lambda')

        for rule_name in rule_names:
            print("Testing "+rule_name)

            #Get CI JSON from either the CLI or one of the stored templates.
            my_cis = self.__get_test_CIs(rule_name)

            my_parameters = {}
            if self.args.test_parameters:
                my_parameters = json.loads(self.args.test_parameters)

            for my_ci in my_cis:
                print ("\t\tTesting CI " + my_ci['resourceType'])

                #Generate test event from templates
                test_event = json.load(open(os.path.join(path.dirname(__file__), 'template', event_template_filename), 'r'), strict=False)
                my_invoking_event = json.loads(test_event['invokingEvent'])
                my_invoking_event['configurationItem'] = my_ci
                my_invoking_event['notificationCreationTime'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
                test_event['invokingEvent'] = json.dumps(my_invoking_event)
                test_event['ruleParameters'] = json.dumps(my_parameters)

                #Get the Lambda function associated with the Rule
                my_lambda_name = self.__get_stack_name_from_rule_name(rule_name)
                my_lambda_arn = self.__get_lambda_arn_for_stack(my_lambda_name)

                #Call Lambda function with test event.
                result = my_lambda_client.invoke(
                    FunctionName=my_lambda_arn,
                    InvocationType='RequestResponse',
                    LogType='Tail',
                    Payload=json.dumps(test_event)
                )

                #If there's an error dump execution logs to the terminal, if not print out the value returned by the lambda function.
                if 'FunctionError' in result:
                    print(base64.b64decode(str(result['LogResult'])))
                else:
                    print("\t\t\t" + result['Payload'].read())
                    if self.args.verbose:
                        print(base64.b64decode(str(result['LogResult'])))
        return 0

    def status(self):
        print ("Running status!")
        return 0

    def sample_ci(self):
        self.args = get_sample_ci_parser().parse_args(self.args.command_args, self.args)

        my_test_ci = TestCI(self.args.ci_type)
        print(json.dumps(my_test_ci.get_json(), indent=4))

    def logs(self):
        self.args = get_logs_parser().parse_args(self.args.command_args, self.args)

        self.args.rulename = self.__clean_rule_name(self.args.rulename)

        my_session = self.__get_boto_session()
        cw_logs = my_session.client('logs')
        log_group_name = self.__get_log_group_name()

        #Retrieve the last number of log events as specified by the user.
        try:
            log_streams = cw_logs.describe_log_streams(
                logGroupName = log_group_name,
                orderBy = 'LastEventTime',
                descending = True,
                limit = int(self.args.number) #This is the worst-case scenario if there is only one event per stream
            )

            #Sadly we can't just use filter_log_events, since we don't know the timestamps yet and filter_log_events doesn't appear to support ordering.
            my_events = self.__get_log_events(cw_logs, log_streams, int(self.args.number))

            latest_timestamp = 0

            if (my_events is None):
                print("No Events to display.")
                return(0)

            for event in my_events:
                if event['timestamp'] > latest_timestamp:
                    latest_timestamp = event['timestamp']

                self.__print_log_event(event)

            if self.args.follow:
                try:
                    while True:
                        #Wait 2 seconds
                        time.sleep(2)

                        #Get all events between now and the timestamp of the most recent event.
                        my_new_events = cw_logs.filter_log_events(
                            logGroupName = log_group_name,
                            startTime = latest_timestamp+1,
                            endTime = int(time.time())*1000,
                            interleaved = True)


                        for event in my_new_events['events']:
                            if 'timestamp' in event:
                                #Get the timestamp on the most recent event.
                                if event['timestamp'] > latest_timestamp:
                                    latest_timestamp = event['timestamp']

                                #Print the event.
                                self.__print_log_event(event)
                except KeyboardInterrupt as k:
                    sys.exit(0)

        except cw_logs.exceptions.ResourceNotFoundException as e:
            print(e.response['Error']['Message'])

    def rulesets(self):
        self.args = get_rulesets_parser().parse_args(self.args.command_args, self.args)

        if self.args.subcommand in ['add','remove'] and (not self.args.ruleset or not self.args.rulename):
            print("You must specify a ruleset name and a rule for the `add` and `remove` commands.")
            return 1

        if self.args.subcommand == "list":
            self.__list_rulesets()
        elif self.args.subcommand == "add":
            self.__add_ruleset_rule(self.args.ruleset, self.args.rulename)
        elif self.args.subcommand == "remove":
            self.__remove_ruleset_rule(self.args.ruleset, self.args.rulename)
        else :
            print("Unknown subcommand.")

    def create_terraform_template(self):
        self.args = get_create_rule_template_parser().parse_args(self.args.command_args, self.args)

        if self.args.rulesets:
            self.args.rulesets = self.args.rulesets.split(',')

        print ("Generating Terraform template!")

        template = self.__generate_terraform_shell(args)

        rule_names = self.__get_rule_list_for_command()

        for rule_name in rule_names:
            rule_input_params = self.__generate_rule_terraform_params(rule_name)
            rule_def = self.__generate_rule_terraform(rule_name)
            template.append(rule_input_params)
            template.append(rule_def)

        output_file = open(self.args.output_file, 'w')
        output_file.write(json.dumps(template, indent=2))
        print("CloudFormation template written to " + self.args.output_file)

    def create_rule_template(self):
        self.args = get_create_rule_template_parser().parse_args(self.args.command_args, self.args)

        if self.args.rulesets:
            self.args.rulesets = self.args.rulesets.split(',')

        print ("Generating CloudFormation template!")

        #First add the common elements - description, parameters, and resource section header
        template = {}
        template["AWSTemplateFormatVersion"] = "2010-09-09"
        template["Description"] = "AWS CloudFormation template to create custom AWS Config rules. You will be billed for the AWS resources used if you create a stack from this template."

        optional_parameter_group = {
            "Label": { "default": "Optional" },
            "Parameters": []
        }

        required_parameter_group = {
            "Label": { "default": "Required" },
            "Parameters": []
        }

        parameters = {}
        parameters["LambdaAccountId"] = {}
        parameters["LambdaAccountId"]["Description"] = "Account ID that contains Lambda functions for Config Rules."
        parameters["LambdaAccountId"]["Type"] = "String"
        parameters["LambdaAccountId"]["MinLength"] = "12"
        parameters["LambdaAccountId"]["MaxLength"] = "12"

        resources = {}
        conditions = {}

        if not self.args.rules_only:
            #Create Config Role
            resources["ConfigRole"] = {}
            resources["ConfigRole"]["Type"] = "AWS::IAM::Role"
            resources["ConfigRole"]["DependsOn"] = "ConfigBucket"
            resources["ConfigRole"]["Properties"] = {
                "RoleName": config_role_name,
                "Path": "/rdk/",
                "ManagedPolicyArns": [
                    {"Fn::Sub": "arn:${AWS::Partition}:iam::aws:policy/service-role/AWSConfigRole"},
                    {"Fn::Sub": "arn:${AWS::Partition}:iam::aws:policy/ReadOnlyAccess"}
                ],
                "AssumeRolePolicyDocument": CONFIG_ROLE_ASSUME_ROLE_POLICY_DOCUMENT,
                "Policies": [
                    {
                        "PolicyName": "DeliveryPermission",
                        "PolicyDocument": CONFIG_ROLE_POLICY_DOCUMENT
                    }
                ]
            }

            #Create Bucket for Config Data
            resources["ConfigBucket"] = {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "BucketName" : {"Fn::Sub": config_bucket_prefix+"-${AWS::AccountId}-${AWS::Region}" }
                }
            }

            #Create ConfigurationRecorder and DeliveryChannel
            resources["ConfigurationRecorder"] = {
                "Type": "AWS::Config::ConfigurationRecorder",
                "Properties": {
                    "Name": "default",
                    "RoleARN": {"Fn::GetAtt": ["ConfigRole", "Arn"]},
                    "RecordingGroup": {
                        "AllSupported":True,
                        "IncludeGlobalResourceTypes": True
                    }
                }
            }
            if self.args.config_role_arn:
                resources["ConfigurationRecorder"]["Properties"]["RoleARN"] = self.args.config_role_arn

            resources["DeliveryChannel"] = {
                "Type": "AWS::Config::DeliveryChannel",
                "Properties": {
                    "Name": "default",
                    "S3BucketName": {"Ref": "ConfigBucket"},
                    "ConfigSnapshotDeliveryProperties": {
                        "DeliveryFrequency":"One_Hour"
                    }
                }
            }

        #Next, go through each rule in our rule list and add the CFN to deploy it.
        rule_names = self.__get_rule_list_for_command()
        for rule_name in rule_names:
            params, tags = self.__get_rule_parameters(rule_name)
            input_params = json.loads(params["InputParameters"])
            for input_param in input_params:
                cfn_param = {}
                cfn_param["Description"] = "Pass-through to required Input Parameter " + input_param + " for Config Rule " + rule_name
                if len(input_params[input_param].strip()) == 0:
                    default = "<REQUIRED>"
                else:
                    default = input_params[input_param]
                cfn_param["Default"] = default
                cfn_param["Type"] = "String"
                cfn_param["MinLength"] = 1
                cfn_param["ConstraintDescription"] = "This parameter is required."

                param_name = self.__get_alphanumeric_rule_name(rule_name)+input_param
                parameters[param_name] = cfn_param
                required_parameter_group["Parameters"].append(param_name)

            if "OptionalParameters" in params:
                optional_params = json.loads(params["OptionalParameters"])
                for optional_param in optional_params:
                    cfn_param = {}
                    cfn_param["Description"] = "Pass-through to optional Input Parameter " + optional_param + " for Config Rule " + rule_name
                    cfn_param["Default"] = optional_params[optional_param]
                    cfn_param["Type"] = "String"

                    param_name = self.__get_alphanumeric_rule_name(rule_name)+optional_param

                    parameters[param_name] = cfn_param
                    optional_parameter_group["Parameters"].append(param_name)

                    conditions[param_name] = {
                        "Fn::Not": [
                            {
                                "Fn::Equals": [
                                    "",
                                    {
                                        "Ref": param_name
                                    }
                                ]
                            }
                        ]
                    }

            config_rule = {}
            config_rule["Type"] = "AWS::Config::ConfigRule"
            if not self.args.rules_only:
                config_rule["DependsOn"] = "DeliveryChannel"

            properties = {}
            source = {}
            source["SourceDetails"] = []

            properties["ConfigRuleName"] = rule_name
            properties["Description"] = rule_name

            #Create the SourceDetails stanza.
            if 'SourceEvents' in params:
                #If there are SourceEvents specified for the Rule, generate the Scope clause.
                source_events = params['SourceEvents'].split(",")
                properties["Scope"] = {"ComplianceResourceTypes": source_events}

                #Also add the appropriate event source.
                source["SourceDetails"].append(
                {
                  "EventSource": "aws.config",
                  "MessageType": "ConfigurationItemChangeNotification"
                })
            if 'SourcePeriodic' in params:
                source["SourceDetails"].append(
                    {
                      "EventSource": "aws.config",
                      "MessageType": "ScheduledNotification",
                      "MaximumExecutionFrequency": params["SourcePeriodic"]
                    }
                )

            #If it's a Managed Rule it will have a SourceIdentifier string in the params and we need to set the source appropriately.  Otherwise, set the source to our custom lambda function.
            if 'SourceIdentifier' in params:
                source["Owner"] = "AWS"
                source["SourceIdentifier"] = params['SourceIdentifier']
                del source["SourceDetails"]
            else:
                source["Owner"] = "CUSTOM_LAMBDA"
                source["SourceIdentifier"] = { "Fn::Sub": "arn:${AWS::Partition}:lambda:${AWS::Region}:${LambdaAccountId}:function:RDK-Rule-Function-"+self.__get_stack_name_from_rule_name(rule_name) }

            properties["Source"] = source

            properties["InputParameters"] = {}

            if "InputParameters" in params:
                for required_param in json.loads(params["InputParameters"]):
                    cfn_param_name = self.__get_alphanumeric_rule_name(rule_name)+required_param
                    properties["InputParameters"][required_param] = { "Ref": cfn_param_name }

            if "OptionalParameters" in params:
                for optional_param in json.loads(params["OptionalParameters"]):
                    cfn_param_name = self.__get_alphanumeric_rule_name(rule_name)+optional_param
                    properties["InputParameters"][optional_param] = {
                        "Fn::If": [
                            cfn_param_name,
                            {
                                "Ref": cfn_param_name
                            },
                            {
                                "Ref": "AWS::NoValue"
                            }
                        ]
                    }


            config_rule["Properties"] = properties
            config_rule_resource_name = self.__get_alphanumeric_rule_name(rule_name)+"ConfigRule"
            resources[config_rule_resource_name] = config_rule

            if "Remediation" in params:
                remediation = self.__create_remediation_cloudformation_block(params["Remediation"])
                remediation["DependsOn"] = [config_rule_resource_name]
                if not self.args.rules_only:
                    remediation["DependsOn"].append("ConfigRole")

                resources[self.__get_alphanumeric_rule_name(rule_name)+"Remediation"] = remediation

        template["Resources"] = resources
        template["Conditions"] = conditions
        template["Parameters"] = parameters
        template["Metadata"] = {
            "AWS::CloudFormation::Interface": {
                "ParameterGroups": [
                    {
                        "Label": {
                            "default": "Lambda Account ID"
                        },
                        "Parameters": [
                            "LambdaAccountId"
                        ]
                    },
                    required_parameter_group,
                    optional_parameter_group
                ],
                "ParameterLabels": {
                    "LambdaAccountId": { "default": "REQUIRED: Account ID that contains Lambda Function(s) that back the Rules in this template."}
                }
            }
        }

        output_file = open(self.args.output_file, 'w')
        output_file.write(json.dumps(template, indent=2))
        print("CloudFormation template written to " + self.args.output_file)

    def __generate_terraform_shell(self, args):
        return ""

    def __generate_rule_terraform(self, rule_name):
        return ""

    def __generate_rule_terraform_params(self, rule_name):
        return ""

    def __remove_ruleset_rule(self, ruleset, rulename):
        params, tags = self.__get_rule_parameters(rulename)
        if 'RuleSets' in params:
            if self.args.ruleset in params['RuleSets']:
                params['RuleSets'].remove(self.args.ruleset)
            else :
                print("Rule " + rulename + " is not in RuleSet " + ruleset)
        else:
            print("Rule " + rulename + " is not in any RuleSets")

        self.__write_params_file(rulename, params, tags)

        print(rulename + " removed from RuleSet " + ruleset)

    def __add_ruleset_rule(self, ruleset, rulename):
        params, tags = self.__get_rule_parameters(rulename)
        if 'RuleSets' in params:
            if self.args.ruleset in params['RuleSets']:
                print("Rule is already in the specified RuleSet.")
            else :
                params['RuleSets'].append(self.args.ruleset)
        else:
            rulesets = [self.args.ruleset]
            params['RuleSets'] = rulesets

        self.__write_params_file(rulename, params, tags)

        print(rulename + " added to RuleSet " + ruleset)

    def __list_rulesets(self):
        rulesets = []
        rules = []

        for obj_name in os.listdir('.'):
            #print(obj_name)
            params_file_path = os.path.join('.', obj_name, parameter_file_name)
            if os.path.isfile(params_file_path):
                parameters_file = open(params_file_path, 'r')
                my_params = json.load(parameters_file)
                parameters_file.close()
                if 'RuleSets' in my_params['Parameters']:
                    rulesets.extend(my_params['Parameters']['RuleSets'])

                    if self.args.ruleset in my_params['Parameters']['RuleSets']:
                        #print("Found rule! " + obj_name)
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
        return os.path.join(path.dirname(__file__), 'template')

    def __create_test_suite(self, test_dir):
        tests = []
        for (top, dirs, filenames) in os.walk(test_dir):
            for filename in fnmatch.filter(filenames, '*_test.py'):
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
            output = output.rstrip('/')

        return output

    def __create_java_rule(self):
        src = os.path.join(path.dirname(__file__), 'template', 'runtime', 'java8','src')
        dst = os.path.join(os.getcwd(), rules_dir, self.args.rulename, 'src')
        shutil.copytree(src, dst)

        src = os.path.join(path.dirname(__file__), 'template',  'runtime', 'java8','jars')
        dst = os.path.join(os.getcwd(), rules_dir, self.args.rulename, 'jars')
        shutil.copytree(src, dst)

        src = os.path.join(path.dirname(__file__), 'template',  'runtime', 'java8', 'build.gradle')
        dst = os.path.join(os.getcwd(), rules_dir, self.args.rulename, 'build.gradle')
        shutil.copyfile(src, dst)

    def __create_dotnet_rule(self):
        runtime_path = os.path.join(path.dirname(__file__), 'template',  'runtime', self.args.runtime)
        dst_path = os.path.join(os.getcwd(), rules_dir, self.args.rulename)
        for obj in os.listdir(runtime_path):
            src = os.path.join(runtime_path, obj)
            dst = os.path.join(dst_path, obj)
            if os.path.isfile(src):
                shutil.copyfile(src, dst)
            else :
                shutil.copytree(src, dst)

    def __print_log_event(self, event):
        time_string = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event['timestamp']/1000))

        rows = 24
        columns = 80
        try:
            rows, columns = os.popen('stty size', 'r').read().split()
        except ValueError as e:
            #This was probably being run in a headless test environment which had no stty.
            print("Using default terminal rows and columns.")

        line_wrap = int(columns) - 22
        message_lines = str(event['message']).splitlines()
        formatted_lines = []

        for line in message_lines:
            line = line.replace('\t','    ')
            formatted_lines.append('\n'.join(line[i:i+line_wrap] for i in range(0, len(line), line_wrap)))

        message_string = '\n'.join(formatted_lines)
        message_string = message_string.replace('\n','\n                      ')

        print(time_string + " - " + message_string)

    def __get_log_events(self, my_client, log_streams, number_of_events):
        event_count = 0
        log_events = []
        for stream in log_streams['logStreams']:
            #Retrieve the logs for this stream.
            events = my_client.get_log_events(
                logGroupName = self.__get_log_group_name(),
                logStreamName = stream['logStreamName'],
                limit = int(number_of_events)

            )
            #Go through the logs and add events to my output array.
            for event in events['events']:
                log_events.append(event)
                event_count = event_count + 1

                #Once we have enough events, stop.
                if event_count >= number_of_events:
                    return log_events

        #If more records were requested than exist, return as many as we found.
        return log_events

    def __get_log_group_name(self):
        return '/aws/lambda/RDK-Rule-Function-' + self.args.rulename

    def __get_boto_session(self):
        session_args = {}

        if self.args.region:
            session_args['region_name'] = self.args.region

        if self.args.profile:
            session_args['profile_name']=self.args.profile
        elif self.args.access_key_id and self.args.secret_access_key:
            session_args['aws_access_key_id']=self.args.access_key_id
            session_args['aws_secret_access_key']=self.args.secret_access_key

        return boto3.session.Session(**session_args)

    def __get_caller_identity_details(self, session):
        my_sts = session.client('sts')
        response = my_sts.get_caller_identity()
        arn_split = response['Arn'].split(':')

        return {
            'account_id': response['Account'],
            'partition': arn_split[1],
            'region': arn_split[3]
        }

    def __get_stack_name_from_rule_name(self, rule_name):
        output = rule_name.replace("_","")

        return output

    def __get_alphanumeric_rule_name(self, rule_name):
        output = rule_name.replace("_","").replace("-","")

        return output

    def __get_rule_list_for_command(self):
        rule_names = []
        if self.args.all:
            d = '.'
            for obj_name in os.listdir('.'):
                obj_path = os.path.join('.', obj_name)
                if os.path.isdir(obj_path) and not obj_name == 'rdk':
                    for file_name in os.listdir(obj_path):
                        if obj_name not in rule_names:
                            if os.path.exists(os.path.join(obj_path, 'parameters.json')):
                                rule_names.append(obj_name)
                            else:
                                if file_name.split('.')[0] == obj_name:
                                    rule_names.append(obj_name)
                                if os.path.exists(os.path.join(obj_path, 'src', 'main', 'java', 'com', 'rdk', 'RuleCode.java')):
                                    rule_names.append(obj_name)
                                if os.path.exists(os.path.join(obj_path, 'RuleCode.cs')):
                                    rule_names.append(obj_name)
        elif self.args.rulesets:
            for obj_name in os.listdir('.'):
                params_file_path = os.path.join('.', obj_name, parameter_file_name)
                if os.path.isfile(params_file_path):
                    parameters_file = open(params_file_path, 'r')
                    my_params = json.load(parameters_file)
                    parameters_file.close()
                    if 'RuleSets' in my_params['Parameters']:
                        s_input = set(self.args.rulesets)
                        s_params = set(my_params['Parameters']['RuleSets'])
                        if s_input.intersection(s_params):
                            rule_names.append(obj_name)
        elif self.args.rulename:
            for rule_name in self.args.rulename:
                cleaned_rule_name = self.__clean_rule_name(rule_name)
                if os.path.isdir(cleaned_rule_name):
                    rule_names.append(cleaned_rule_name)
        else:
            print ('Invalid Option: Specify Rule Name or RuleSet. Run "rdk deploy -h" for more info.')
            sys.exit(1)

        if len(rule_names) == 0:
            print("No matching rule directories found.")
            sys.exit(1)

        #Check rule names to make sure none are too long.  This is needed to catch Rules created before length constraint was added.
        for name in rule_names:
            if len(name) > 45:
                print("Error: Found Rule with name over 45 characters: {} \n Recreate the Rule with a shorter name.".format(name))
                sys.exit(1)

        return rule_names

    def __get_rule_parameters(self, rule_name):
        params_file_path = os.path.join(os.getcwd(), rules_dir, rule_name, parameter_file_name)

        try:
            parameters_file = open(params_file_path, 'r')
        except IOError as e:
            print("Failed to open parameters file for rule '{}'".format(rule_name))
            print(e.message)
            sys.exit(1)

        my_json = {}

        try:
            my_json = json.load(parameters_file)
        except ValueError as ve:  # includes simplejson.decoder.JSONDecodeError
            print("Failed to decode JSON in parameters file for Rule {}".format(rule_name))
            print(ve.message)
            parameters_file.close()
            sys.exit(1)
        except Exception as e:
            print("Error loading parameters file for Rule {}".format(rule_name))
            print(e.message)
            parameters_file.close()
            sys.exit(1)

        parameters_file.close()

        my_tags = my_json.get('Tags', None)

        #Needed for backwards compatibility with earlier versions of parameters file
        if my_tags is None:
            my_tags = "[]"
            my_json['Parameters']['Tags'] = my_tags

        #as my_tags was returned as a string in earlier versions, convert it back to a list
        if isinstance(my_tags, basestring):
            my_tags = json.loads(my_tags)

        return my_json['Parameters'], my_tags

    def __parse_rule_args(self, is_required):
        self.args = get_rule_parser(is_required, self.args.command).parse_args(self.args.command_args, self.args)

        if self.args.rulename:
            if len(self.args.rulename) > 45:
                print("Rule names must be 45 characters or fewer.")
                sys.exit(1)

        resource_type_error = ""
        if self.args.resource_types:
            for resource_type in self.args.resource_types.split(','):
                if resource_type not in accepted_resource_types:
                    resource_type_error = resource_type_error + ' "' + resource_type + '" not found in list of accepted resource types.\n'
            if resource_type_error:
                print(resource_type_error)
                sys.exit(1)

        if is_required and not self.args.resource_types and not self.args.maximum_frequency:
            print("You must specify either a resource type trigger or a maximum frequency.")
            sys.exit(1)

        if self.args.input_parameters:
            try:
                input_params_dict = json.loads(self.args.input_parameters, strict=False)
            except Exception as e:
                print("Failed to parse input parameters.")
                sys.exit(1)

        if self.args.optional_parameters:
            try:
                optional_params_dict = json.loads(self.args.optional_parameters, strict=False)
            except Exception as e:
                print("Failed to parse optional parameters.")
                sys.exit(1)

        if self.args.rulesets:
            self.args.rulesets = self.args.rulesets.split(',')

    def __parse_test_args(self):
        self.args = get_test_parser(self.args.command).parse_args(self.args.command_args, self.args)

        if self.args.all and self.args.rulename:
            print("You may specify either specific rules or --all, but not both.")
            return 1

        if self.args.rulesets:
            self.args.rulesets = self.args.rulesets.split(',')

        return self.args

    def __parse_deploy_args(self, ForceArgument=False):

        self.args = get_deployment_parser(ForceArgument).parse_args(self.args.command_args, self.args)

        ### Validate inputs ###
        if self.args.stack_name and not self.args.functions_only:
            print("--stack-name can only be specified when using the --functions-only feature.")
            sys.exit(1)

        #Make sure we're not exceeding Layer limits
        if self.args.lambda_layers:
            layer_count = len(self.args.lambda_layers.split(","))
            if layer_count > 5:
                print("You may only specify 5 Lambda Layers.")
                sys.exit(1)
            if self.args.rdklib_layer_arn and layer_count > 4:
                print("Because you have selected a 'lib' runtime You may only specify 4 additional Lambda Layers.")
                sys.exit(1)

        #RDKLib version and RDKLib Layer ARN are mutually exclusive.
        if "rdk_lib_version" in self.args and "rdklib_layer_arn" in self.args:
            print("Specify EITHER an RDK Lib version to use the official release OR a specific Layer ARN to use a custom implementation.")
            sys.exit(1)

        #Check rule names to make sure none are too long.  This is needed to catch Rules created before length constraint was added.
        if self.args.rulename:
            for name in self.args.rulename:
                if len(name) > 45:
                    print("Error: Found Rule with name over 45 characters: {} \n Recreate the Rule with a shorter name.".format(name))
                    sys.exit(1)

        if self.args.functions_only and not self.args.stack_name:
            self.args.stack_name = "RDK-Config-Rule-Functions"

        if self.args.rulesets:
            self.args.rulesets = self.args.rulesets.split(',')

    def __populate_params(self):
        #create custom session based on whatever credentials are available to us
        my_session = self.__get_boto_session()

        #get accountID
        #my_sts = my_session.client('sts')
        #response = my_sts.get_caller_identity()
        #account_id = response['Account']

        my_input_params = {}

        if self.args.input_parameters:
            #Parse the input parameters to make sure it's valid json.  Be tolerant of quote usage in the input string.
            try:
                my_input_params = json.loads(self.args.input_parameters, strict=False)
            except Exception as e:
                print("Error parsing input parameter JSON.  Make sure your JSON keys and values are enclosed in properly-escaped double quotes and your input-parameters string is enclosed in single quotes.")
                raise e

        my_optional_params = {}

        if self.args.optional_parameters:
            #As above, but with the optional input parameters.
            try:
                my_optional_params = json.loads(self.args.optional_parameters, strict=False)
            except Exception as e:
                print("Error parsing optional input parameter JSON.  Make sure your JSON keys and values are enclosed in properly escaped double quotes and your optional-parameters string is enclosed in single quotes.")

        my_tags = []

        if self.args.tags:
            #As above, but with the optional tag key value pairs.
            try:
                my_tags = json.loads(self.args.tags, strict=False)
            except Exception as e:
                print("Error parsing optional tags JSON.  Make sure your JSON keys and values are enclosed in properly escaped double quotes and tags string is enclosed in single quotes.")

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
                    "remediation_parameters"
                ]
            )
            and not self.args.remediation_action
        ):
            print("Remediation Flags detected but no remeditaion action (--remediation-action) set")

        if self.args.remediation_action:
            try:
                my_remediation = self.__generate_remediation_params()
            except Exception as e:
                print("Error parsing remediation configuration.")

        #create config file and place in rule directory
        parameters = {
            'RuleName': self.args.rulename,
            'SourceRuntime': self.args.runtime,
            #'CodeBucket': code_bucket_prefix + account_id,
            'CodeKey': self.args.rulename+'.zip',
            'InputParameters': json.dumps(my_input_params),
            'OptionalParameters': json.dumps(my_optional_params)
        }

        tags = json.dumps(my_tags)

        if self.args.resource_types:
            parameters['SourceEvents'] = self.args.resource_types

        if self.args.maximum_frequency:
            parameters['SourcePeriodic'] = self.args.maximum_frequency

        if self.args.rulesets:
            parameters['RuleSets'] = self.args.rulesets

        if self.args.source_identifier:
            parameters['SourceIdentifier'] = self.args.source_identifier
            parameters['CodeKey'] = None
            parameters['SourceRuntime'] = None

        if my_remediation:
            parameters['Remediation'] = my_remediation

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
        my_params = {
            "Version": "1.0",
            "Parameters": parameters,
            "Tags": tags
        }
        params_file_path = os.path.join(os.getcwd(), rules_dir, rulename, parameter_file_name)
        parameters_file = open(params_file_path, 'w')
        json.dump(my_params, parameters_file, indent=2)
        parameters_file.close()

    def __wait_for_cfn_stack(self, cfn_client, stackname):
        in_progress = True
        while in_progress:
            my_stacks = []
            response = cfn_client.list_stacks()

            for stack in response["StackSummaries"]:
                if stack['StackName'] == stackname:
                    my_stacks.append(stack)

            #Find the stack (if any) that hasn't already been deleted.
            all_deleted = True
            active_stack = None
            for stack in my_stacks:
                if stack['StackStatus'] != 'DELETE_COMPLETE':
                    active_stack = stack
                    all_deleted = False

            #If all stacks have been deleted, clearly we're done!
            if all_deleted:
                in_progress = False
                print("CloudFormation stack operation complete.")
                continue
            else:
                if 'FAILED' in active_stack['StackStatus']:
                    in_progress = False
                    print("CloudFormation stack operation Failed for " + stackname +".")
                    if 'StackStatusReason' in active_stack:
                        print("Reason: " + active_stack['StackStatusReason'])
                elif active_stack['StackStatus'] == 'ROLLBACK_COMPLETE':
                    in_progress = False
                    print("CloudFormation stack operation Rolled Back for " + stackname +".")
                    if 'StackStatusReason' in active_stack:
                        print("Reason: " + active_stack['StackStatusReason'])
                elif 'COMPLETE' in active_stack['StackStatus']:
                    in_progress = False
                    print("CloudFormation stack operation complete.")
                else:
                    print("Waiting for CloudFormation stack operation to complete...")
                    time.sleep(5)

    def __get_handler(self, rule_name, params):
        if params['SourceRuntime'] in ['python2.7', 'python3.6', 'python3.6-lib', 'python3.7', 'nodejs4.3', 'nodejs6.10', 'nodejs8.10']:
            return (rule_name+'.lambda_handler')
        elif params['SourceRuntime'] in ['java8']:
            return ('com.rdk.RuleUtil::handler')
        elif params['SourceRuntime'] in ['dotnetcore1.0','dotnetcore2.0']:
            return ('csharp7.0::Rdk.CustomConfigHandler::FunctionHandler')

    def __get_runtime_string(self, params):
        if params['SourceRuntime'] in ['python3.6-lib', 'python3.6-managed']:
            return 'python3.6'

        return params['SourceRuntime']

    def __get_test_CIs(self, rulename):
        test_ci_list = []
        if self.args.test_ci_types:
            print("\tTesting with generic CI for supplied Resource Type(s)")
            ci_types = self.args.test_ci_types.split(",")
            for ci_type in ci_types:
                my_test_ci = TestCI(ci_type)
                test_ci_list.append(my_test_ci.get_json())
        else:
            #Check to see if there is a test_ci.json file in the Rule directory
            tests_path = os.path.join(os.getcwd(), rules_dir, rulename, test_ci_filename)
            if os.path.exists(tests_path):
                print("\tTesting with CI's provided in test_ci.json file. NOT YET IMPLEMENTED") #TODO
            #    test_ci_list self._load_cis_from_file(tests_path)
            else:
                print("\tTesting with generic CI for configured Resource Type(s)")
                my_rule_params, my_rule_tags = self.__get_rule_parameters(rulename)
                ci_types = str(my_rule_params['SourceEvents']).split(",")
                for ci_type in ci_types:
                    my_test_ci = TestCI(ci_type)
                    test_ci_list.append(my_test_ci.get_json())

        return test_ci_list

    def __get_lambda_arn_for_stack(self, stack_name):
        #create custom session based on whatever credentials are available to us
        my_session = self.__get_boto_session()

        my_cfn = my_session.client('cloudformation')

        #Since CFN won't detect changes to the lambda code stored in S3 as a reason to update the stack, we need to manually update the code reference in Lambda once the CFN has run.
        self.__wait_for_cfn_stack(my_cfn, stack_name)

        #Lamba function is an output of the stack.
        my_updated_stack = my_cfn.describe_stacks(StackName=stack_name)
        cfn_outputs = my_updated_stack['Stacks'][0]['Outputs']
        my_lambda_arn = 'NOTFOUND'
        for output in cfn_outputs:
            if output['OutputKey'] == 'RuleCodeLambda':
                my_lambda_arn = output['OutputValue']

        if my_lambda_arn == 'NOTFOUND':
            print("Could not read CloudFormation stack output to find Lambda function.")
            sys.exit(1)

        return my_lambda_arn

    def __get_lambda_arn_for_rule(self, rule_name, partition, region, account):
        return "arn:{}:lambda:{}:{}:function:RDK-Rule-Function-{}".format(partition, region, account, self.__get_stack_name_from_rule_name(rule_name))

    def __delete_package_file(self, file):
        try:
            os.remove(file)
        except OSError:
            pass

    def __upload_function_code(self, rule_name, params, account_id, session, code_bucket_name):
        if params['SourceRuntime'] == "java8":
            #Do java build and package.
            print ("Running Gradle Build for "+rule_name)
            working_dir = os.path.join(os.getcwd(), rules_dir, rule_name)
            command = ["gradle","build"]
            subprocess.call( command, cwd=working_dir)

            #set source as distribution zip
            s3_src = os.path.join(os.getcwd(), rules_dir, rule_name, 'build', 'distributions', rule_name+".zip")
        elif params['SourceRuntime'] in ["dotnetcore1.0","dotnetcore2.0"]:
            print ("Packaging "+rule_name)
            working_dir = os.path.join(os.getcwd(), rules_dir, rule_name)
            commands = [["dotnet","restore"]]

            app_runtime = "netcoreapp1.0"
            if params['SourceRuntime'] == "dotnetcore2.0":
                app_runtime = "netcoreapp2.0"

            commands.append(["dotnet","lambda","package","-c","Release","-f", app_runtime])

            for command in commands:
                subprocess.call( command, cwd=working_dir)

            # Remove old zip file if it already exists
            package_file_dst = os.path.join(rule_name, rule_name+".zip")
            self.__delete_package_file(package_file_dst)

            # Create new package in temp directory, copy to rule directory
            # This copy avoids the archiver trying to include the output zip in itself
            s3_src_dir = os.path.join(os.getcwd(),rules_dir, rule_name,'bin','Release', app_runtime, 'publish')
            tmp_src = shutil.make_archive(os.path.join(tempfile.gettempdir(), rule_name), 'zip', s3_src_dir)
            shutil.copy(tmp_src, package_file_dst)
            s3_src = os.path.abspath(package_file_dst)
            self.__delete_package_file(tmp_src)

        else:
            print ("Zipping " + rule_name)
            # Remove old zip file if it already exists
            package_file_dst = os.path.join(rule_name, rule_name+".zip")
            self.__delete_package_file(package_file_dst)

            #zip rule code files and upload to s3 bucket
            s3_src_dir = os.path.join(os.getcwd(), rules_dir, rule_name)
            tmp_src = shutil.make_archive(os.path.join(tempfile.gettempdir(), rule_name), 'zip', s3_src_dir)
            shutil.copy(tmp_src, package_file_dst)
            s3_src = os.path.abspath(package_file_dst)
            self.__delete_package_file(tmp_src)

        s3_dst = "/".join((rule_name, rule_name+".zip"))

        my_s3 = session.resource('s3')

        print ("Uploading " + rule_name)
        my_s3.meta.client.upload_file(s3_src, code_bucket_name, s3_dst)
        print ("Upload complete.")

        return s3_dst

    def __create_remediation_cloudformation_block(self, remediation_config):
        remediation = {
            "Type" : "AWS::Config::RemediationConfiguration",
            "DependsOn": "rdkConfigRule",
            "Properties" : remediation_config
        }

        return remediation

    def __create_function_cloudformation_template(self):
        print ("Generating CloudFormation template for Lambda Functions!")

        #First add the common elements - description, parameters, and resource section header
        template = {}
        template["AWSTemplateFormatVersion"] = "2010-09-09"
        template["Description"] = "AWS CloudFormation template to create Lamdba functions for backing custom AWS Config rules. You will be billed for the AWS resources used if you create a stack from this template."

        parameters = {}
        parameters["SourceBucket"] = {}
        parameters["SourceBucket"]["Description"] = "Name of the S3 bucket that you have stored the rule zip files in."
        parameters["SourceBucket"]["Type"] = "String"
        parameters["SourceBucket"]["MinLength"] = "1"
        parameters["SourceBucket"]["MaxLength"] = "255"

        template["Parameters"] = parameters

        resources = {}

        if self.args.lambda_role_arn:
            print ("Existing IAM role provided: " + self.args.lambda_role_arn)
        else:
            print ("No IAM role provided, creating a new IAM role for lambda function")
            lambda_role = {}
            lambda_role["Type"] = "AWS::IAM::Role"
            lambda_role["Properties"] = {}
            lambda_role["Properties"]["Path"] = "/rdk/"
            lambda_role["Properties"]["AssumeRolePolicyDocument"] = {
              "Version": "2012-10-17",
              "Statement": [ {
                "Sid": "AllowLambdaAssumeRole",
                "Effect": "Allow",
                "Principal": { "Service": "lambda.amazonaws.com" },
                "Action": "sts:AssumeRole"
              } ]
            }
            lambda_policy_statements =[
                {
                    "Sid": "1",
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Effect": "Allow",
                    "Resource": { "Fn::Sub": "arn:${AWS::Partition}:s3:::${SourceBucket}/*" }
                },
                {
                    "Sid": "2",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogStreams"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Sid": "3",
                    "Action": [
                        "config:PutEvaluations"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Sid": "4",
                    "Action": [
                        "iam:List*",
                        "iam:Describe*",
                        "iam:Get*"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Sid": "5",
                    "Action": [
                        "sts:AssumeRole"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ]
            if self.args.lambda_subnets and self.args.lambda_security_groups:
                vpc_policy={
                    "Sid": "LambdaVPCAccessExecution",
                    "Action": [
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DeleteNetworkInterface",
                        "ec2:CreateNetworkInterface"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
                lambda_policy_statements.append(vpc_policy)
            lambda_role["Properties"]["Policies"] = [{
              "PolicyName": "ConfigRulePolicy",
              "PolicyDocument": {
                "Version": "2012-10-17",
                "Statement": lambda_policy_statements
              }
            } ]
            lambda_role["Properties"]["ManagedPolicyArns"] = [{"Fn::Sub": "arn:${AWS::Partition}:iam::aws:policy/ReadOnlyAccess"}]
            resources["rdkLambdaRole"] = lambda_role

        rule_names = self.__get_rule_list_for_command()
        for rule_name in rule_names:
            alphanum_rule_name = self.__get_alphanumeric_rule_name(rule_name)
            stack_name = self.__get_stack_name_from_rule_name(rule_name)
            params, tags = self.__get_rule_parameters(rule_name)

            if 'SourceIdentifier' in params:
                print("Skipping Managed Rule.")
                continue

            lambda_function = {}
            lambda_function["Type"] = "AWS::Lambda::Function"
            properties = {}
            properties["FunctionName"] = "RDK-Rule-Function-" + stack_name
            properties["Code"] = {"S3Bucket": { "Ref": "SourceBucket"}, "S3Key": rule_name+"/"+rule_name+".zip"}
            properties["Description"] = "Function for AWS Config Rule " + rule_name
            properties["Handler"] = self.__get_handler(rule_name, params)
            properties["MemorySize"] = "256"
            if self.args.lambda_role_arn:
                properties["Role"] = self.args.lambda_role_arn
            else:
                lambda_function["DependsOn"] = "rdkLambdaRole"
                properties["Role"] = {"Fn::GetAtt": [ "rdkLambdaRole", "Arn" ]}
            properties["Runtime"] = self.__get_runtime_string(params)
            properties["Timeout"] = 300
            properties["Tags"] = tags
            if self.args.lambda_subnets and self.args.lambda_security_groups:
                properties["VpcConfig"] = {
                    "SecurityGroupIds" : self.args.lambda_security_groups.split(","),
                    "SubnetIds" : self.args.lambda_subnets.split(",")
                }
            layers = []
            if self.args.rdklib_layer_arn:
                layers.append(self.args.rdklib_layer_arn)
            if self.args.lambda_layers:
                for layer in self.args.lambda_layers.split(','):
                    layers.append(layer)
            if layers:
                properties["Layers"] = layers

            lambda_function["Properties"] = properties
            resources[alphanum_rule_name+"LambdaFunction"] = lambda_function

            lambda_permissions = {}
            lambda_permissions["Type"] = "AWS::Lambda::Permission"
            lambda_permissions["DependsOn"] = alphanum_rule_name+"LambdaFunction"
            lambda_permissions["Properties"] = {
                "FunctionName": {"Fn::GetAtt": [ alphanum_rule_name+"LambdaFunction", "Arn" ] },
                "Action": "lambda:InvokeFunction",
                "Principal": "config.amazonaws.com"
            }
            resources[alphanum_rule_name+"LambdaPermissions"]=lambda_permissions

        template['Resources'] = resources

        return json.dumps(template, indent=2)

class TestCI():
    def __init__(self, ci_type):
        #convert ci_type string to filename format
        ci_file = ci_type.replace('::','_') + '.json'
        try:
            self.ci_json = json.load(open(os.path.join(path.dirname(__file__), 'template',  example_ci_dir, ci_file), 'r'))
        except FileNotFoundError:
            print("No sample CI found for " + ci_type + ", even though it appears to be a supported CI.  Please log an issue at https://github.com/awslabs/aws-config-rdk.")
            exit(1)

    def get_json(self):
        return self.ci_json
