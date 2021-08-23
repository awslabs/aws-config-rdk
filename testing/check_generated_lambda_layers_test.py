import boto3
import sys

rule_list = [
    {"rule": "LP3_TestRule_P38_lib", "runtime": "python3.8"},
    {"rule": "LP3_TestRule_P37_lib", "runtime": "python3.7"},
    {"rule": "LP3_TestRule_P36_lib", "runtime": "python3.6"},
]

lambda_client = boto3.client("lambda")
response = lambda_client.list_layer_versions(LayerName="rdklib-layer")
if not response["LayerVersions"]:
    print("Not Found")
    sys.exit(1)
print("Found!")

for rule in rule_list:
    runtime = rule["runtime"]
    rule_lambda_name = "RDK-Rule-Function-" + rule["rule"].replace("_", "")
    lambda_config = lambda_client.get_function(FunctionName=rule_lambda_name)["Configuration"]
    if runtime != lambda_config["Runtime"]:
        print("Deployed a lambda with the wrong runtime")
        sys.exit(1)
    found_layer = False
    for layer in lambda_config["Layers"]:
        if "rdklib-layer" in layer["Arn"]:
            found_layer = True
    if not found_layer:
        print("Deployed a lambda without the required layer")
        sys.exit(1)
