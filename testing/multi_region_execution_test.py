# Set up test directory
import sys

import boto3

test_file_name = "test-region.yaml"

cfn_client_ap_east = boto3.client("cloudformation", region_name="ap-southeast-1")
stack_status_ap_east = cfn_client_ap_east.describe_stacks(StackName="MFAENABLEDRULE")
print(stack_status_ap_east)
if stack_status_ap_east["Stacks"][0]["StackStatus"] not in ["CREATE_COMPLETE", "UPDATE_COMPLETE"]:
    sys.exit(1)

cfn_client_us_west = boto3.client("cloudformation", region_name="us-west-1")
stack_status_us_west = cfn_client_us_west.describe_stacks(StackName="MFAENABLEDRULE")
print(stack_status_us_west)
if stack_status_us_west["Stacks"][0]["StackStatus"] not in ["CREATE_COMPLETE", "UPDATE_COMPLETE"]:
    sys.exit(1)
