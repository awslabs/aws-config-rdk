import boto3
import subprocess

testing_regions = {
    "aws": ["us-east-1", "ap-southeast-1", "eu-central-1", "sa-east-1"],
    "aws-cn": ["cn-north-1", "cn-northwest-1"],
    "aws-us-gov": ["us-gov-west-1", "us-gov-east-1"],
}
sts_client = boto3.client("sts")
partition = sts_client.get_caller_identity()["Arn"].split(":")[1]

for region in testing_regions[partition]:
    subprocess.Popen(["rdk", "-r", region, "init"])
