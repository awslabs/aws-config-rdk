@ECHO OFF
setlocal EnableDelayedExpansion
if "%~2"=="" goto args_count_wrong
if "%~3"=="" goto args_count_correct
if "%~4"=="" goto args_count_wrong

:args_count_wrong
ECHO Usage: evaluateRuleAndGetLogs.cmd PROFILE RULE_NAME
ECHO example: setup.cmd default desiredInstanceTypeRule 
ECHO Use "default" for PROFILE if you want to use the default profile
Exit /B 1

:args_count_correct
SET PROFILE=%1
SET RULE_NAME=%2
ECHO Evaluating rule %RULE_NAME%
aws --profile %PROFILE% configservice start-config-rules-evaluation --config-rule-name %RULE_NAME%
for /l %%A IN (1,1,4) DO (
   ECHO Waiting for rule to be evaluated
   timeout /t 3 /nobreak > NUL
)
SET COUNT=1
for /f %%i in ('aws --profile %PROFILE% logs describe-log-streams --log-group-name /aws/lambda/%RULE_NAME% --order-by LastEventTime --descending --max-items 1 --query logStreams[*].[logStreamName] --output text') DO (
  if !COUNT!==1 (
    aws --profile %PROFILE% logs get-log-events --log-group-name /aws/lambda/%RULE_NAME% --log-stream-name %%i
  )
  SET /a COUNT=!COUNT!+1
)