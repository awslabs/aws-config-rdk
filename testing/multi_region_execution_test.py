import os

# Set up test directory
import sys

cwd = os.getcwd()
test_dir = os.path.join(cwd, "multi_region_test")
os.mkdir(test_dir)
os.chdir(test_dir)

# create region file
test_file = """
default:
  - ap-east-1
  - us-west-2
test-commercial:
  - ap-east-1
  - us-west-1
"""

with open("region.yaml") as f:
    f.write(test_file)

# run rdk init in default region
init_command = f"rdk -f {test_file} init"
init_return_code = os.system(init_command)

if init_return_code != 0:
    sys.exit(1)

# rdk create MFA_ENABLED_RULE --runtime python3.7 --resource-types AWS::IAM::User
create_return_code = os.system("rdk create MFA_ENABLED_RULE --runtime python3.8 --resource-types AWS::IAM::User")

if create_return_code != 0:
    sys.exit(1)

# run rdk deploy in test-commercial
deploy_command = f"rdk -f {test_file} -i test-commercial deploy MFA_ENABLED_RULE"
deploy_return_code = os.system(deploy_command)

if deploy_return_code != 0:
    sys.exit(1)

# rdk undeploy in test-commercial
undeploy_command = f"rdk -f {test_file} -i test-commercial undeploy --force MFA_ENABLED_RULE"
undeploy_return_code = os.system(undeploy_command)

if undeploy_return_code != 0:
    sys.exit(1)
