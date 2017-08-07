@ECHO OFF
setlocal EnableDelayedExpansion
if "%~2"=="" goto args_count_wrong
if "%~3"=="" goto args_count_correct

:args_count_wrong
ECHO Usage: createRule.cmd RULE_NAME APPLICABLE_RESOURCE_TYPES(eg. createRule.cmd requiredTagsRule "AWS::EC2::Instance,AWS::EC2::VPC")
Exit /B 1

:args_count_correct
SET RULE_NAME=%1
SET RESOURCE_TYPES=%2
SET RESOURCE_TYPES=%RESOURCE_TYPES:"=%
SET RESOURCE_TYPES=%RESOURCE_TYPES:,=","%
SET RESOURCE_TYPES=["!RESOURCE_TYPES!"]
CScript  ruleUtil\executeZip.vbs  "%CD%\ruleCode"  "%CD%\lambda.zip" > NUL
aws iam get-role --role-name config_lambda_basic_execution > NUL 2>&1
if errorlevel 1 (
   ECHO Creating/Updating IAM role config_lambda_basic_execution
   aws iam create-role --role-name config_lambda_basic_execution --assume-role-policy-document file://ruleUtil/lambdaTrustPolicy.json > NUL 2>&1
   aws iam attach-role-policy --role-name config_lambda_basic_execution --policy-arn arn:aws:iam::aws:policy/service-role/AWSConfigRulesExecutionRole
   aws iam attach-role-policy --role-name config_lambda_basic_execution --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
   for /l %%A IN (1,1,5) DO (
      ECHO Waiting for IAM role to propagate
      timeout /t 8 /nobreak > NUL
   )
)
for /f %%i in ('aws iam get-role --role-name config_lambda_basic_execution --query Role.Arn --output text') do SET LAMBDA_ROLE_ARN=%%i
ECHO Creating/Updating Lambda function %RULE_NAME%
aws lambda create-function --function-name %RULE_NAME% --zip-file fileb://lambda.zip --runtime python3.6 --role !LAMBDA_ROLE_ARN! --handler rule_code.lambda_handler > NUL 2>&1
aws lambda update-function-code --function-name %RULE_NAME% --zip-file fileb://lambda.zip > NUL 
aws lambda add-permission --function-name %RULE_NAME% --statement-id 1 --principal config.amazonaws.com --action lambda:InvokeFunction > NUL 2>&1
for /f %%i in ('aws lambda get-function --function-name %RULE_NAME% --query Configuration.FunctionArn --output text') do SET LAMBDA_ARN=%%i
for /F "delims=" %%a in (ruleUtil/configRule.json) do (
   set "CONFIG_RULE=!CONFIG_RULE!%%a"
)
for /F "delims=" %%a in (ruleCode/ruleParameters.txt) do (
   set "RULE_PARAMETERS=!RULE_PARAMETERS!%%a"
)
SET RULE_PARAMETERS=!RULE_PARAMETERS:"=\"!
SET CONFIG_RULE=!CONFIG_RULE:RULE_NAME="%RULE_NAME%"!
SET CONFIG_RULE=!CONFIG_RULE:RESOURCE_TYPES=%RESOURCE_TYPES%!
SET CONFIG_RULE=!CONFIG_RULE:LAMBDA_ARN="%LAMBDA_ARN%"!
SET CONFIG_RULE=!CONFIG_RULE:RULE_PARAMETERS=%RULE_PARAMETERS%!
SET CONFIG_RULE=!CONFIG_RULE:"=""!
SET CONFIG_RULE=!CONFIG_RULE:\=\\!
ECHO Creating/Updating Config rule %RULE_NAME%
aws configservice put-config-rule --config-rule "!CONFIG_RULE!"
ECHO(
ECHO Rule %RULE_NAME% created/updated. Ignore any "already exists" messages.
