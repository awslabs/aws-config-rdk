# Developer Notes

These notes are intended to help RDK developers update the repository consistently.

## New Runtime Support Process

These instructions document the parts of the repository that need to be updated when support for a new Lambda runtime is added.

### Update pyproject.toml

- Add to `classifiers` list:

```yaml
"Programming Language :: Python :: <VER>,"
```

- Add to `include` list:

```yaml
"rdk/template/runtime/python<VER>/*",
"rdk/template/runtime/python<VER>-lib/*",
```

### Update README.md

- Update documentation and examples

### Update rdk.py

- Update references to include new version

### Update Linux and Windows Buildspec files (`testing` folder)

- Add new test cases for the new version

## New Version Release Process (for Maintainers)

To release a new version of RDK...

1. Update `pyproject.toml` with the new version number
2. Update `rdk/__init__.py` with the new version number
3. Locally `git pull origin master` to ensure you have the latest code
4. Locally `git tag <new version number> && git push origin <new version number>` to create a tagged version, which will kick off the remaining workflows.

## Running RDK from source

1. Clone the RDK repo from git
2. Make your changes
3. `poetry build` # builds a wheel package inside of the dist folder
4. `pip install --force-reinstall <path to your .whl file>` # optionally, use `--user` to install for just the current user.

## Manual Testing Scenarios

Note: before running these, make sure to set your AWS credentials and region appropriately.

These are not a replacement for unit tests, but because RDK inherently relies on CloudFormation, some level of end-to-end testing is necessary.

1. Basic periodic custom rule creation and deployment
```powershell
$rule="myAutomationTest" # This is gitignored
$runtime="python3.13"
$frequency="TwentyFour_Hours"
rdk create $rule --runtime $runtime --maximum-frequency $frequency
rdk deploy $rule
# It should deploy a CloudFormation stack successfully.
rdk undeploy $rule --force
Remove-Item $rule -recurse
```
2. Basic configuration-change custom rule creation and deployment
```powershell
$rule="myAutomationTest" # This is gitignored
$runtime="python3.13"
$test_event_type = "AWS::EC2::Instance"
rdk create $rule --runtime $runtime --resource-types $test_event_type
rdk deploy $rule
# It should deploy a CloudFormation stack successfully.
rdk undeploy $rule --force
Remove-Item $rule -recurse
```
3. Managed rule creation and deployment
```powershell
$rule="myAutomationTest" # This is gitignored
$managed_rule="ACCESS_KEYS_ROTATED"
$frequency="TwentyFour_Hours"
rdk create $rule --source-identifier $managed_rule --maximum-frequency $frequency
rdk deploy $rule
# It should deploy a CloudFormation stack successfully.
rdk undeploy $rule --force
Remove-Item $rule -recurse
```

4. Deploy a proactive rule
```powershell
$rule="myAutomationTest" # This is gitignored
$runtime="python3.13"
$test_event_type = "AWS::S3::Bucket"
$evaluation_mode="PROACTIVE"
rdk create $rule --runtime $runtime --evaluation-mode $evaluation_mode --resource-types $test_event_type
rdk deploy $rule
# It should deploy a CloudFormation stack successfully.
rdk undeploy $rule --force
Remove-Item $rule -recurse # clean up the directory for future testing
```

5. Deploy a proactive rule as a periodic rule (should fail)
```powershell
$rule="myAutomationTest" # This is gitignored
$runtime="python3.13"
$evaluation_mode="BOTH"
$frequency="TwentyFour_Hours"
rdk create $rule --runtime $runtime --evaluation-mode $evaluation_mode --maximum-frequency $frequency
# It should fail at create time
```

6. Deploy a proactive managed rule
```powershell
$rule="myAutomationTest" # This is gitignored
$managed_rule="S3_BUCKET_LOGGING_ENABLED"
$evaluation_mode="BOTH"
$test_event_type = "AWS::S3::Bucket"
rdk create $rule --source-identifier $managed_rule --resource-types $test_event_type --evaluation-mode $evaluation_mode
rdk deploy $rule
# It should deploy a CloudFormation stack successfully.
rdk undeploy $rule --force
Remove-Item $rule -recurse
```

7. Deploy a proactive managed Organization rule
```powershell
$rule="myAutomationTest" # This is gitignored
$managed_rule="S3_BUCKET_LOGGING_ENABLED"
$evaluation_mode="PROACTIVE"
$test_event_type = "AWS::S3::Bucket"
$test_management_account = "730335412016"
rdk create $rule --source-identifier $managed_rule --resource-types $test_event_type --evaluation-mode $evaluation_mode
rdk deploy-organization $rule --excluded-accounts $test_management_account
# It should fail to deploy due to an unsupported evaluation mode.
Remove-Item $rule -recurse
```