@ECHO OFF
setlocal EnableDelayedExpansion
aws cloudformation create-stack --stack-name config-setup-stack --capabilities CAPABILITY_NAMED_IAM --template-body file://configSetup.json 
SET STACK_STATUS=CREATE_IN_PROGRESS
:stackCreating
if !STACK_STATUS! == CREATE_IN_PROGRESS (
    for /f %%i in ('aws cloudformation describe-stacks --stack-name config-setup-stack --query Stacks[0].StackStatus --output text') do SET STACK_STATUS=%%i
    ECHO Config setup stack status: !STACK_STATUS!
    ::timeout /t 5 /nobreak > NUL
    goto :stackCreating
)
aws configservice start-configuration-recorder --configuration-recorder-name default
ECHO Config setup completed
