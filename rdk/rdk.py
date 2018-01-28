#    Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
#
#        http://aws.amazon.com/apache2.0/
#
#    or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

import os
from os import path
import sys
import shutil
import boto3
import json
import time
import imp
import argparse
from botocore.exceptions import ClientError
from datetime import datetime
import base64
import ast
import textwrap
import fileinput
import subprocess
from subprocess import call


rdk_dir = '.rdk'
rules_dir = ''
tests_dir = ''
util_filename = 'rule_util'
rule_handler = 'rule_code'
rule_template = 'rdk-rule.template'
config_bucket_prefix = 'config-bucket-'
config_role_name = 'config-role'
assume_role_policy_file = 'configRoleAssumeRolePolicyDoc.json'
delivery_permission_policy_file = 'deliveryPermissionsPolicy.json'
code_bucket_prefix = 'config-rule-code-bucket-'
parameter_file_name = 'parameters.json'
example_ci_dir = 'example_ci'
test_ci_filename = 'test_ci.json'
event_template_filename = 'test_event_template.json'

class rdk():
    def __init__(self, args):
        self.args = args

    def process_command(self):
        method_to_call = getattr(self, self.args.command.replace('-','_'))
        exit_code = method_to_call()

        return(exit_code)

    def init(self):
        parser = argparse.ArgumentParser(
            prog='rdk '+self.args.command,
            description = 'Sets up AWS Config and turn current directory into a rdk working directory.  This will enable configuration recording in AWS.')
        self.args = parser.parse_args(self.args.command_args, self.args)

        print ("Running init!")

        #if the .rdk directory exists, delete it.
        if  os.path.exists(rdk_dir):
            shutil.rmtree(rdk_dir)

        #copy contents of template directory into .rdk directory
        src = os.path.join(path.dirname(__file__), 'template')
        dst = rdk_dir
        shutil.copytree(src, dst)

        #create custom session based on whatever credentials are available to us
        my_session = self.__get_boto_session()

        #Create our ConfigService client
        my_config = my_session.client('config')

        #get accountID
        my_sts = my_session.client('sts')
        response = my_sts.get_caller_identity()
        account_id = response['Account']

        config_recorder_exists = False
        config_recorder_name = "default"
        config_role_arn = ""
        delivery_channel_exists = False
        config_bucket_exists = False

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
            print("Found Bucket: " + config_bucket_name)
            config_bucket_exists = True

        my_s3 = my_session.client('s3')

        if not config_bucket_exists:
            #create config bucket
            config_bucket_name = config_bucket_prefix + account_id
            response = my_s3.list_buckets()
            bucket_exists = False
            for bucket in response['Buckets']:
                if bucket['Name'] == config_bucket_name:
                    bucket_exists = True

            if not bucket_exists:
                print('Creating Config bucket '+config_bucket_name )
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
                assume_role_policy = open(os.path.join(rdk_dir, assume_role_policy_file), 'r').read()
                my_iam.create_role(RoleName=config_role_name, AssumeRolePolicyDocument=assume_role_policy, Path="/rdk/")

            #attach role policy
            my_iam.attach_role_policy(RoleName=config_role_name, PolicyArn='arn:aws:iam::aws:policy/service-role/AWSConfigRole')
            policy_template = open(os.path.join(rdk_dir, delivery_permission_policy_file), 'r').read()
            delivery_permissions_policy = policy_template.replace('ACCOUNTID', account_id)
            my_iam.put_role_policy(RoleName=config_role_name, PolicyName='ConfigDeliveryPermissions', PolicyDocument=delivery_permissions_policy)

            #wait for changes to propagate.
            print('Waiting for IAM role to propagate')
            time.sleep(16)

        #create or update config recorder
        if not config_role_arn:
            config_role_arn = "arn:aws:iam::"+account_id+":role/rdk/config-role"

        my_config.put_configuration_recorder(ConfigurationRecorder={'name':config_recorder_name, 'roleARN':config_role_arn, 'recordingGroup':{'allSupported':True, 'includeGlobalResourceTypes': True}})

        if not delivery_channel_exists:
            #create delivery channel
            my_config.put_delivery_channel(DeliveryChannel={'name':'default', 's3BucketName':config_bucket_name, 'configSnapshotDeliveryProperties':{'deliveryFrequency':'Six_Hours'}})

        #start config recorder
        my_config.start_configuration_recorder(ConfigurationRecorderName=config_recorder_name)
        print('Config Service is ON')

        print('Config setup complete.')

        #create code bucket
        code_bucket_name = code_bucket_prefix + account_id + my_session.region_name
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

    def create(self):
        #Parse the command-line arguments relevant for creating a Config Rule.
        self.__parse_rule_args(True)

        print ("Running create!")

        if not self.args.runtime:
            print("Runtime is required for 'create' command.")
            return 1

        extension_mapping = {'java8':'.java', 'python2.7':'.py', 'python3.6':'.py','nodejs4.3':'.js', 'dotnetcore1.0':'cs', 'dotnetcore2.0':'cs'}
        if self.args.runtime not in extension_mapping:
            print ("rdk does nto support that runtime yet.")

        if not self.args.maximum_frequency:
            self.args.maximum_frequency = "TwentyFour_Hours"
            print("Defaulting to TwentyFour_Hours Maximum Frequency.")

        #create rule directory.
        rule_path = os.path.join(os.getcwd(), rules_dir, self.args.rulename)
        if os.path.exists(rule_path):
            print("Local Rule directory already exists.")
            return 1

        try:
            os.makedirs(os.path.join(os.getcwd(), rules_dir, self.args.rulename))

            #copy rule template into rule directory
            if self.args.runtime == 'java8':
                self.__create_java_rule()
            elif self.args.runtime in ['dotnetcore1.0', 'dotnetcore2.0']:
                self.__create_dotnet_rule()
            else:
                src = os.path.join(os.getcwd(), rdk_dir, 'runtime', self.args.runtime, rule_handler + extension_mapping[self.args.runtime])
                dst = os.path.join(os.getcwd(), rules_dir, self.args.rulename, self.args.rulename + extension_mapping[self.args.runtime])
                shutil.copyfile(src, dst)

                src = os.path.join(os.getcwd(), rdk_dir, 'runtime', self.args.runtime, util_filename + extension_mapping[self.args.runtime])
                if os.path.exists(src):
                    dst = os.path.join(os.getcwd(), rules_dir, self.args.rulename, util_filename + extension_mapping[self.args.runtime])
                    shutil.copyfile(src, dst)

            #Write the parameters to a file in the rule directory.
            self.__write_params_file()

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
        old_params = self.__read_params_file()

        if not self.args.runtime and old_params['Parameters']['SourceRuntime']:
            self.args.runtime = old_params['Parameters']['SourceRuntime']

        if not self.args.maximum_frequency and old_params['Parameters']['SourcePeriodic']:
            self.args.maximum_frequency = old_params['Parameters']['SourcePeriodic']

        if not self.args.resource_types and old_params['Parameters']['SourceEvents']:
            self.args.resource_types = old_params['Parameters']['SourceEvents']

        if not self.args.input_parameters and old_params['Parameters']['InputParameters']:
            self.args.input_parameters = old_params['Parameters']['InputParameters']

        #Write the parameters to a file in the rule directory.
        self.__write_params_file()

        print ("Modified Rule '"+self.args.rulename+"'.  Use the `deploy` command to push your changes to AWS.")

    def deploy(self):
        parser = argparse.ArgumentParser(prog='rdk deploy')
        parser.add_argument('rulename', metavar='<rulename>', nargs='*', help='Rule name(s) to deploy.  Rule(s) will be pushed to AWS.')
        parser.add_argument('--all','-a', action='store_true', help="All rules in the working directory will be deployed.")
        self.args = parser.parse_args(self.args.command_args, self.args)

        #run the deploy code
        print ("Running deploy!")

        rule_names = self.__get_rule_list_for_command()

        #create custom session based on whatever credentials are available to us
        my_session = self.__get_boto_session()

        #get accountID
        my_sts = my_session.client('sts')
        response = my_sts.get_caller_identity()
        account_id = response['Account']
        for rule_name in rule_names:
            my_rule_params = self.__get_rule_parameters(rule_name)
            s3_src = ""

            if my_rule_params['SourceRuntime'] == "java8":
                #Do java build and package.
                print ("Running Gradle Build for "+rule_name)
                working_dir = os.path.join(os.getcwd(), rules_dir, rule_name)
                command = ["gradle","build"]
                subprocess.call( command, cwd=working_dir)

                #set source as distribution zip
                s3_src = os.path.join(os.getcwd(), rules_dir, rule_name, 'build', 'distributions', rule_name+".zip")
            elif my_rule_params['SourceRuntime'] in ["dotnetcore1.0","dotnetcore2.0"]:
                print ("Packaging "+rule_name)
                working_dir = os.path.join(os.getcwd(), rules_dir, rule_name)
                commands = [["dotnet","restore"]]

                app_runtime = "netcoreapp1.0"
                if my_rule_params['SourceRuntime'] == "dotnetcore2.0":
                    app_runtime = "netcoreapp2.0"

                commands.append(["dotnet","lambda","package","-c","Release","-f", app_runtime])

                for command in commands:
                    subprocess.call( command, cwd=working_dir)

                s3_src_dir = os.path.join(os.getcwd(),rules_dir, rule_name,'bin','Release', app_runtime, 'publish')
                s3_src = shutil.make_archive(os.path.join(rule_name, rule_name), 'zip', s3_src_dir)
            else:
                print ("Zipping " + rule_name)
                #zip rule code files and upload to s3 bucket
                s3_src_dir = os.path.join(os.getcwd(), rules_dir, rule_name)
                s3_src = shutil.make_archive(os.path.join(rule_name, rule_name), 'zip', s3_src_dir)

            s3_dst = "/".join(rule_name, rule_name+".zip")
            code_bucket_name = code_bucket_prefix + account_id + my_session.region_name
            my_s3 = my_session.resource('s3')

            print ("Uploading " + rule_name)
            my_s3.meta.client.upload_file(s3_src, code_bucket_name, s3_dst)

            #create CFN Parameters
            source_events = "NONE"
            if 'SourceEvents' in my_rule_params:
                source_events = my_rule_params['SourceEvents']

            my_params = [
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
                    'ParameterValue': my_rule_params['SourceRuntime'],
                },
                {
                    'ParameterKey': 'SourceEvents',
                    'ParameterValue': source_events,
                },
                {
                    'ParameterKey': 'SourcePeriodic',
                    'ParameterValue': my_rule_params['SourcePeriodic'],
                },
                {
                    'ParameterKey': 'SourceInputParameters',
                    'ParameterValue': my_rule_params['InputParameters'],
                },
                {
                    'ParameterKey': 'SourceHandler',
                    'ParameterValue': self.__get_handler(rule_name, my_rule_params)
                }]

            #deploy config rule
            cfn_body = os.path.join(os.getcwd(), rdk_dir, "configRole.json")
            my_cfn = my_session.client('cloudformation')

            try:
                my_stack = my_cfn.describe_stacks(StackName=rule_name)
                #If we've gotten here, stack exists and we should update it.
                print ("Updating CloudFormation Stack for " + rule_name)
                try:
                    response = my_cfn.update_stack(
                        StackName=rule_name,
                        TemplateBody=open(cfn_body, "r").read(),
                        Parameters=my_params,
                        Capabilities=[
                            'CAPABILITY_IAM',
                        ],
                    )
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

                my_lambda_arn = self.__get_lambda_arn_for_rule(rule_name)

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
                response = my_cfn.create_stack(
                    StackName=rule_name,
                    TemplateBody=open(cfn_body, "r").read(),
                    Parameters=my_params,
                    Capabilities=[
                        'CAPABILITY_IAM',
                    ],
                )

            #wait for changes to propagate.
            self.__wait_for_cfn_stack(my_cfn, rule_name)

        print('Config deploy complete.')

        return 0

    def test_local(self):
        print ("Running test_local!")
        self.__parse_test_args()

        #Dynamically import the shared rule_util module.
        util_path = os.path.join(rdk_dir, "rule_util.py")
        imp.load_source('rule_util', util_path)

        #Construct our list of rules to test.
        rule_names = self.__get_rule_list_for_command()

        for rule_name in rule_names:
            print("Testing "+rule_name)
            #Dynamically import the custom rule code, so that we can run the evaluate_compliance function.
            module_path = os.path.join(".", os.path.dirname(rules_dir), rule_name, rule_name+".py")
            module_name = str(rule_name).lower()
            module = imp.load_source(module_name, module_path)

            #Get CI JSON from either the CLI or one of the stored templates.
            my_cis = self.__get_test_CIs(rule_name)

            #Get Parameters from Rule config
            my_rule_params = self.__get_rule_parameters(rule_name)
            my_parameters = my_rule_params['InputParameters']

            #Execute the evaluate_compliance function
            for my_ci in my_cis:
                print ("\t\tTesting CI " + my_ci['resourceType'])
                result = getattr(module, 'evaluate_compliance')(my_ci, my_parameters)
                print("\t\t\t"+result)

        return 0

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
                test_event = json.load(open(os.path.join(os.getcwd(), rdk_dir, event_template_filename), 'r'), strict=False)
                my_invoking_event = json.loads(test_event['invokingEvent'])
                my_invoking_event['configurationItem'] = my_ci
                my_invoking_event['notificationCreationTime'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
                test_event['invokingEvent'] = json.dumps(my_invoking_event)
                test_event['ruleParameters'] = json.dumps(my_parameters)

                #Get the Lambda function associated with the Rule
                my_lambda_arn = self.__get_lambda_arn_for_rule(rule_name)

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
        parser = argparse.ArgumentParser(prog='rdk '+self.args.command)
        parser.add_argument('ci_type', metavar='<resource type>', help='Resource name (e.g. "AWS::EC2::Instance") to display a sample CI JSON document for.')
        self.args = parser.parse_args(self.args.command_args, self.args)

        my_test_ci = TestCI(self.args.ci_type)
        print(json.dumps(my_test_ci.get_json(), indent=4))

    def logs(self):
        parser = argparse.ArgumentParser(
            prog='rdk '+self.args.command,
            usage="rdk "+self.args.command + " <rulename> [-n/--number NUMBER] [-f/--follow]")
        parser.add_argument('rulename', metavar='<rulename>', help='Rule whose logs will be displayed')
        parser.add_argument('-f','--follow',  action='store_true', help='Continuously poll Lambda logs and write to stdout.')
        parser.add_argument('-n','--number',  default=3, help='Number of previous logged events to display.')
        self.args = parser.parse_args(self.args.command_args, self.args)

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

    def __clean_rule_name(self, rule_name):
        output = rule_name
        if output[-1:] == "/":
            print("Removing trailing '/'")
            output = output.rstrip('/')

        return output

    def __create_java_rule(self):
        src = os.path.join(os.getcwd(), rdk_dir, 'runtime', 'java8','src')
        dst = os.path.join(os.getcwd(), rules_dir, self.args.rulename, 'src')
        shutil.copytree(src, dst)

        src = os.path.join(os.getcwd(), rdk_dir, 'runtime', 'java8','jars')
        dst = os.path.join(os.getcwd(), rules_dir, self.args.rulename, 'jars')
        shutil.copytree(src, dst)

        src = os.path.join(os.getcwd(), rdk_dir, 'runtime', 'java8', 'build.gradle')
        dst = os.path.join(os.getcwd(), rules_dir, self.args.rulename, 'build.gradle')
        shutil.copyfile(src, dst)

    def __create_dotnet_rule(self):
        runtime_path = os.path.join(os.getcwd(), rdk_dir, 'runtime', self.args.runtime)
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

        rows, columns = os.popen('stty size', 'r').read().split()
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

    def __get_rule_list_for_command(self):
        rule_names = []
        if self.args.all:
            d = '.'
            for obj_name in os.listdir('.'):
                obj_path = os.path.join('.', obj_name)
                if os.path.isdir(obj_path) and not obj_name == 'rdk':
                    for file_name in os.listdir(obj_path):
                        if obj_name not in rule_names:
                            if file_name.split('.')[0] == obj_name:
                                rule_names.append(obj_name)
                            if os.path.exists(os.path.join(obj_path, 'src', 'main', 'java', 'com', 'rdk', 'RuleCode.java')):
                                rule_names.append(obj_name)
                            if os.path.exists(os.path.join(obj_path, 'RuleCode.cs')):
                                rule_names.append(obj_name)
        else:
            rule_names.append(self.__clean_rule_name(self.args.rulename[0]))

        return rule_names

    def __get_rule_parameters(self, rule_name):
        params_file_path = os.path.join(os.getcwd(), rules_dir, rule_name, parameter_file_name)
        parameters_file = open(params_file_path, 'r')
        my_json = json.load(parameters_file)
        parameters_file.close()
        return my_json['Parameters']

    def __parse_rule_args(self, is_required):
        usage_string = "[--runtime <runtime>] [--resource-types <resource types>] [--maximum-frequency <max execution frequency>] [--input-parameters <parameter JSON>]"

        if is_required:
            usage_string = "--runtime <runtime> --resource-types <resource types> [optional configuration flags]"

        parser = argparse.ArgumentParser(
            prog='rdk '+self.args.command,
            usage="rdk "+self.args.command + " <rulename> " + usage_string
        )
        parser.add_argument('rulename', metavar='<rulename>', help='Rule name to create/modify')
        parser.add_argument('-R','--runtime', required=is_required, help='Runtime for lambda function', choices=['nodejs4.3','java8','python2.7','python3.6','dotnetcore1.0','dotnetcore2.0'])
        parser.add_argument('-r','--resource-types', required=False, help='Resource types that trigger event-based rule evaluation')
        parser.add_argument('-m','--maximum-frequency', help='Maximum execution frequency', choices=['One_Hour','Three_Hours','Six_Hours','Twelve_Hours','TwentyFour_Hours'])
        parser.add_argument('-i','--input-parameters', help="[optional] JSON for Config parameters for testing.")
        self.args = parser.parse_args(self.args.command_args, self.args)

    def __parse_test_args(self):
        parser = argparse.ArgumentParser(prog='rdk '+self.args.command)
        parser.add_argument('rulename', metavar='<rulename>[,<rulename>,...]', nargs='*', help='Rule name(s) to test')
        parser.add_argument('--all','-a', action='store_true', help="Test will be run against all rules in the working directory.")
        parser.add_argument('--test-ci-json', '-j', help="[optional] JSON for test CI for testing.")
        parser.add_argument('--test-ci-types', '-t', help="[optional] CI type to use for testing.")
        parser.add_argument('--verbose', '-v', action='store_true', help='Enable full log output')
        self.args = parser.parse_args(self.args.command_args, self.args)

        if self.args.all and self.args.rulename:
            print("You may specify either specific rules or --all, but not both.")
            return 1

    def __write_params_file(self):
        #create custom session based on whatever credentials are available to us
        my_session = self.__get_boto_session()

        #get accountID
        my_sts = my_session.client('sts')
        response = my_sts.get_caller_identity()
        account_id = response['Account']

        my_input_params = {}

        if self.args.input_parameters:
            #Parse the input parameters to make sure it's valid json.  Be tolerant of quote usage in the input string.
            try:
                my_input_params = json.loads(self.args.input_parameters, strict=False)
            except Exception as e:
                print("Error parsing input parameter JSON.  Make sure your JSON keys and values are enclosed in double quotes and your input-parameters string is enclosed in single quotes.")
                raise e

        #create config file and place in rule directory
        parameters = {
            'RuleName': self.args.rulename,
            'SourceRuntime': self.args.runtime,
            #'CodeBucket': code_bucket_prefix + account_id,
            'CodeKey': self.args.rulename+'.zip',
            'InputParameters': json.dumps(my_input_params)
        }

        if self.args.resource_types:
            parameters['SourceEvents'] = self.args.resource_types

        if self.args.maximum_frequency:
            parameters['SourcePeriodic'] = self.args.maximum_frequency

        my_params = {"Parameters": parameters}
        params_file_path = os.path.join(os.getcwd(), rules_dir, self.args.rulename, parameter_file_name)
        parameters_file = open(params_file_path, 'w')
        json.dump(my_params, parameters_file, indent=2)
        parameters_file.close()

    def __read_params_file(self):
        my_params = {}
        params_file_path = os.path.join(os.getcwd(), rules_dir, self.args.rulename, parameter_file_name)
        parameters_file = open(params_file_path, 'r')
        my_params = json.load(parameters_file)
        parameters_file.close()
        return my_params

    def __wait_for_cfn_stack(self, cfn_client, stackname):
        in_progress = True
        while in_progress:
            my_stack = cfn_client.describe_stacks(StackName=stackname)

            if 'IN_PROGRESS' not in my_stack['Stacks'][0]['StackStatus']:
                in_progress = False
            else:
                print("Waiting for CloudFormation stack operation to complete...")
                time.sleep(5)

    def __get_handler(self, rule_name, params):
        if params['SourceRuntime'] in ['python2.7','python3.6','nodejs4.3','nodejs6.10']:
            return (rule_name+'.lambda_handler')
        elif params['SourceRuntime'] in ['java8']:
            return ('com.rdk.RuleUtil::handler')
        elif params['SourceRuntime'] in ['dotnetcore1.0','dotnetcore2.0']:
            return ('csharp7.0::Rdk.CustomConfigHandler::FunctionHandler')

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
                my_rule_params = self.__get_rule_parameters(rulename)
                ci_types = str(my_rule_params['SourceEvents']).split(",")
                for ci_type in ci_types:
                    my_test_ci = TestCI(ci_type)
                    test_ci_list.append(my_test_ci.get_json())

        return test_ci_list

    def __get_lambda_arn_for_rule(self, rulename):
        #create custom session based on whatever credentials are available to us
        my_session = self.__get_boto_session()

        my_cfn = my_session.client('cloudformation')

        #Since CFN won't detect changes to the lambda code stored in S3 as a reason to update the stack, we need to manually update the code reference in Lambda once the CFN has run.
        self.__wait_for_cfn_stack(my_cfn, rulename)

        #Lamba function is an output of the stack.
        my_updated_stack = my_cfn.describe_stacks(StackName=rulename)
        cfn_outputs = my_updated_stack['Stacks'][0]['Outputs']
        my_lambda_arn = 'NOTFOUND'
        for output in cfn_outputs:
            if output['OutputKey'] == 'RuleCodeLambda':
                my_lambda_arn = output['OutputValue']

        if my_lambda_arn == 'NOTFOUND':
            print("Could not read CloudFormation stack output to find Lambda function.")
            sys.exit(1)

        return my_lambda_arn

class TestCI():
    def __init__(self, ci_type):
        #convert ci_type string to filename format
        ci_file = ci_type.replace('::','_') + '.json'
        self.ci_json = json.load(open(os.path.join(rdk_dir, example_ci_dir, ci_file), 'r'))

    def get_json(self):
        return self.ci_json
