@ECHO OFF
setlocal EnableDelayedExpansion
if "%~4"=="" goto args_count_wrong
if "%~5"=="" goto args_count_correct
if "%~6"=="" goto args_count_wrong

:args_count_wrong
ECHO Usage: createRule.cmd PROFILE RUNTIME RULE_NAME APPLICABLE_RESOURCE_TYPES 
ECHO example: createRule.cmd myCLIprofile nodejs desiredInstanceTypeRule "AWS::EC2::Instance,AWS::EC2::VPC"
ECHO Use "default" for PROFILE if you want to use the default profile
Exit /B 1

:args_count_correct
SET PROFILE=%1
SET RUNTIME=%2
SET RULE_NAME=%3
SET RESOURCE_TYPES=%4
if "%RUNTIME%"=="nodejs" (
   SET LAMBDA_RUNTIME="nodejs6.10"
   ) else (
      if "%RUNTIME%"=="python" (
         SET LAMBDA_RUNTIME="python3.6"
      ) else (
         ECHO RUNTIME parameter must be either nodejs or python
         Exit /B 1
      )
   )
) 
SET RESOURCE_TYPES=%RESOURCE_TYPES:"=%
SET RESOURCE_TYPES=%RESOURCE_TYPES:,=","%
SET RESOURCE_TYPES=["!RESOURCE_TYPES!"]
CScript  ruleUtil\executeZip.vbs  "%CD%\ruleCode\%RUNTIME%"  "%CD%\%RULE_NAME%.zip" > NUL
aws --profile %PROFILE% iam get-role --role-name config_lambda_basic_execution > NUL 2>&1
if errorlevel 1 (
   ECHO Creating/Updating IAM role config_lambda_basic_execution
   aws --profile %PROFILE% iam create-role --role-name config_lambda_basic_execution --assume-role-policy-document file://ruleUtil/lambdaTrustPolicy.json > NUL 2>&1
   aws --profile %PROFILE% iam attach-role-policy --role-name config_lambda_basic_execution --policy-arn arn:aws:iam::aws:policy/service-role/AWSConfigRulesExecutionRole
   aws --profile %PROFILE% iam attach-role-policy --role-name config_lambda_basic_execution --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
   for /l %%A IN (1,1,2) DO (
      ECHO Waiting for IAM role to propagate
      timeout /t 8 /nobreak > NUL
   )
)
for /f %%i in ('aws --profile %PROFILE% iam get-role --role-name config_lambda_basic_execution --query Role.Arn --output text') do SET LAMBDA_ROLE_ARN=%%i
ECHO Creating/Updating Lambda function %RULE_NAME%
aws --profile %PROFILE% lambda create-function --function-name %RULE_NAME% --zip-file fileb://%CD%\%RULE_NAME%.zip --runtime %LAMBDA_RUNTIME% --role !LAMBDA_ROLE_ARN! --handler rule_code.lambda_handler > NUL 2>&1
aws --profile %PROFILE% lambda update-function-code --function-name %RULE_NAME% --zip-file fileb://%CD%\%RULE_NAME%.zip > NUL 
aws --profile %PROFILE% lambda add-permission --function-name %RULE_NAME% --statement-id 1 --principal config.amazonaws.com --action lambda:InvokeFunction > NUL 2>&1
for /f %%i in ('aws --profile %PROFILE% lambda get-function --function-name %RULE_NAME% --query Configuration.FunctionArn --output text') do SET LAMBDA_ARN=%%i
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
aws --profile %PROFILE% configservice put-config-rule --config-rule "!CONFIG_RULE!"
ECHO(
ECHO Rule %RULE_NAME% created/updated. Ignore any "already exists" messages.
