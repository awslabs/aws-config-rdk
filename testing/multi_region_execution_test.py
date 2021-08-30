import os
# Set up test directory
import sys

import boto3

test_file_name = "test-region.yaml"
# create region file
test_file = """
default:
  - ap-east-1
  - us-west-2
  - us-east-2
  - us-east-1
  - eu-north-1
test-commercial:
  - ap-east-1
  - us-west-1
  - us-west-2
  - us-east-1
  - eu-north-1
"""

with open(test_file_name, "w+") as f:
    f.write(test_file)

# run rdk init in default region
print("Multi-region test: running init...")
init_command = f"rdk -f {test_file_name} init"
init_return_code = os.system(init_command)

if init_return_code != 0:
    sys.exit(1)

# rdk create MFA_ENABLED_RULE --runtime python3.7 --resource-types AWS::IAM::User
print("Multi-region test: creating rule to test...")
create_return_code = os.system("rdk create MFA_ENABLED_RULE --runtime python3.8 --resource-types AWS::IAM::User")

if create_return_code != 0:
    sys.exit(1)

# run rdk deploy in test-commercial
print("Multi-region test: trying deploy...")
deploy_command = f"rdk -f {test_file_name} --region-set test-commercial deploy MFA_ENABLED_RULE"
deploy_return_code = os.system(deploy_command)

cfn_client_ap_east = boto3.client('cloudformation', region_name='ap-east-1')
stack_status_ap_east = cfn_client_ap_east.describe_stacks(StackName='MFAENABLEDRULE')
if stack_status_ap_east["Stacks"][0]["StackStatus"] != "CREATE_COMPLETE":
    sys.exit(1)

cfn_client_us_west = boto3.client('cloudformation', region_name='us-west-1')
stack_status_us_west = cfn_client_us_west.describe_stacks(StackName='MFAENABLEDRULE')
if stack_status_us_west["Stacks"][0]["StackStatus"] != "CREATE_COMPLETE":
    sys.exit(1)

if deploy_return_code != 0:
    sys.exit(1)

# rdk undeploy in test-commercial
print("Multi-region test: trying undeploy...")
undeploy_command = f"rdk -f {test_file_name} --region-set test-commercial undeploy --force MFA_ENABLED_RULE"
undeploy_return_code = os.system(undeploy_command)

if undeploy_return_code != 0:
    sys.exit(1)
