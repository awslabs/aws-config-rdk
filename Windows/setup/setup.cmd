@ECHO OFF
setlocal EnableDelayedExpansion
if "%~1"=="" goto args_count_wrong
if "%~2"=="" goto args_count_correct
if "%~3"=="" goto args_count_wrong

:args_count_wrong
ECHO Usage: setup.cmd PROFILE
ECHO example: setup.cmd requiredTagsRule "AWS::EC2::Instance,AWS::EC2::VPC"
ECHO Use "default" for PROFILE if you want to use the default profile
Exit /B 1

:args_count_correct
SET PROFILE=%1
for /f %%i in ('aws --profile %PROFILE% sts get-caller-identity --output text --query "Account"') do SET ACCOUNT_ID=%%i
SET BUCKET_NAME=config-bucket-!ACCOUNT_ID!
aws --profile %PROFILE% s3api get-bucket-location --bucket !BUCKET_NAME! > NUL 2>&1
if errorlevel 1 (
   ECHO Creating bucket !BUCKET_NAME!
   aws s3 mb "s3://!BUCKET_NAME!" > NUL 
)
ECHO Creating/Updating IAM role config-role
aws  --profile %PROFILE% iam get-role --role-name config-role > NUL 2>&1
if errorlevel 1 (
   aws --profile %PROFILE% iam create-role --role-name config-role --assume-role-policy-document file://configRoleAssumeRolePolicyDoc.json > NUL 
)
aws --profile %PROFILE% iam attach-role-policy --role-name config-role --policy-arn "arn:aws:iam::aws:policy/service-role/AWSConfigRole"
for /F "delims=" %%a in (deliveryPermissionsPolicy.json) do (
   set "DELIVERY_PERMISSIONS_POLICY=!DELIVERY_PERMISSIONS_POLICY!%%a"
)
SET DELIVERY_PERMISSIONS_POLICY=!DELIVERY_PERMISSIONS_POLICY:ACCOUNTID=%ACCOUNT_ID%!
SET DELIVERY_PERMISSIONS_POLICY=!DELIVERY_PERMISSIONS_POLICY:"=""!
SET DELIVERY_PERMISSIONS_POLICY=!DELIVERY_PERMISSIONS_POLICY:\=\\!
aws --profile %PROFILE% iam put-role-policy --role-name config-role --policy-name ConfigDeliveryPermissions --policy-document "!DELIVERY_PERMISSIONS_POLICY!"
for /l %%A IN (1,1,2) DO (
   ECHO Waiting for IAM role to propagate
   timeout /t 8 /nobreak > NUL
)
ECHO Creating Config ConfigurationRecorder
aws --profile %PROFILE% configservice put-configuration-recorder --configuration-recorder name=default,roleARN="arn:aws:iam::!ACCOUNT_ID!:role/config-role" --recording-group "{\"allSupported\":true,\"includeGlobalResourceTypes\":true}"
ECHO Creating Config DeliveryChannel
aws --profile %PROFILE% configservice put-delivery-channel --delivery-channel "{\"name\": \"default\",\"s3BucketName\": \"!BUCKET_NAME!\",\"configSnapshotDeliveryProperties\":{\"deliveryFrequency\": \"Six_Hours\"}}"
ECHO Config Resources Created
aws --profile %PROFILE% configservice start-configuration-recorder --configuration-recorder-name default
ECHO Config Service is ON

