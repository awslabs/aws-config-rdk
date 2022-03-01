import boto3
import subprocess
import sys

testing_regions = {
    "aws": ["us-east-1", "ap-southeast-1", "eu-central-1", "sa-east-1"],
    "aws-cn": ["cn-north-1", "cn-northwest-1"],
    "aws-us-gov": ["us-gov-west-1", "us-gov-east-1"],
}
sts_client = boto3.client("sts")
arn_array = sts_client.get_caller_identity()["Arn"].split(":")
partition = arn_array[1]
region = arn_array[3]

if region not in testing_regions[partition]:
    testing_regions[partition].append(region)

subprocesses = [subprocess.Popen(["rdk", "-r", region, "init"]) for region in testing_regions[partition]]

received_bad_return_code = False

for process in subprocesses:
    process.wait()
    if process.returncode != 0:
        print(process.communicate())
        received_bad_return_code = True

if received_bad_return_code:
    sys.exit(1)
