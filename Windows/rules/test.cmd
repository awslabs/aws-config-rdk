@ECHO OFF & SETLOCAL
setlocal EnableDelayedExpansion
if "%~1"=="" goto args_count_wrong
if "%~2"=="" goto args_count_correct

:args_count_wrong
ECHO Usage: test.cmd RULE_NAME
Exit /B 1

:args_count_correct
SET RULE_NAME=%1
for %%i IN (testUtil\noncompliantCIs\*) do (
   call :checkCompliance %%i "NON_COMPLIANT"
)
for %%i IN (testUtil\compliantCIs\*) do (
   call :checkCompliance %%i "COMPLIANT"
)

GOTO:EOF

:checkCompliance
   SET FILE=%1
   SET EXPECTED_COMPLIANCE=%2
   SETLOCAL ENABLEDELAYEDEXPANSION
   for /F "delims=" %%a in (!FILE!) do (
      set "ciLine=%%a"
      set "ciLine=!ciLine: =!"
      set "ciLine=!ciLine:"=\\""!"
      set "ci=!ci!!ciLine!"
   )
   for /F "delims=" %%b in (testUtil/testEvent.json) do (
      set "EVENT=!EVENT!%%b"
   )
   for /F "delims=" %%a in (ruleCode/ruleParameters.txt) do (
      set "RULE_PARAMETERS=!RULE_PARAMETERS!%%a"
   )
   SET RULE_PARAMETERS=!RULE_PARAMETERS:"=\"!
   SET "EVENT=!EVENT:RULE_PARAMETERS=%RULE_PARAMETERS%!"
   for %%s in ("!ci!") do (
      SET "EVENT=!EVENT:"=""!"
      SET "EVENT=!EVENT:\=\\!"
      SET "EVENT=!EVENT:CI_PLACEHOLDER=%%~s!"
      break>testUtil/output.txt
      aws lambda invoke --function-name !RULE_NAME! --payload "!EVENT!" testUtil/output.txt > NUL
      SET /p ACTUAL_COMPLIANCE=<testUtil/output.txt
      if !ACTUAL_COMPLIANCE!==!EXPECTED_COMPLIANCE! (
         ECHO PASSED: Expected !EXPECTED_COMPLIANCE!. Actual !ACTUAL_COMPLIANCE!. CI from file !FILE!
      )
      if NOT !ACTUAL_COMPLIANCE!==!EXPECTED_COMPLIANCE! (
         ECHO FAILED: Expected !EXPECTED_COMPLIANCE!. Actual !ACTUAL_COMPLIANCE!. CI from file !FILE!
      )
   ) 
   ENDLOCAL
