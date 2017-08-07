@ECHO OFF
setlocal EnableDelayedExpansion
for /f %%i in ('aws sts get-caller-identity --output text --query "Account"') do SET ACCOUNT_ID=%%i
SET BUCKET_NAME=config-bucket-!ACCOUNT_ID!
aws s3api get-bucket-location --bucket !BUCKET_NAME! > NUL 2>&1
if errorlevel 1 (
   ECHO Creating bucket !BUCKET_NAME!
   aws s3 mb "s3://!BUCKET_NAME!" > NUL 
)
ECHO Creating/Updating IAM role config-role
aws iam get-role --role-name config-role > NUL 2>&1
if errorlevel 1 (
   aws iam create-role --role-name config-role --assume-role-policy-document file://configRoleAssumeRolePolicyDoc.json > NUL 
)
aws iam attach-role-policy --role-name config-role --policy-arn "arn:aws:iam::aws:policy/service-role/AWSConfigRole"
for /F "delims=" %%a in (deliveryPermissionsPolicy.json) do (
   set "DELIVERY_PERMISSIONS_POLICY=!DELIVERY_PERMISSIONS_POLICY!%%a"
)
SET DELIVERY_PERMISSIONS_POLICY=!DELIVERY_PERMISSIONS_POLICY:ACCOUNTID=%ACCOUNT_ID%!
SET DELIVERY_PERMISSIONS_POLICY=!DELIVERY_PERMISSIONS_POLICY:"=""!
SET DELIVERY_PERMISSIONS_POLICY=!DELIVERY_PERMISSIONS_POLICY:\=\\!
aws iam put-role-policy --role-name config-role --policy-name ConfigDeliveryPermissions --policy-document "!DELIVERY_PERMISSIONS_POLICY!"
for /l %%A IN (1,1,5) DO (
   ECHO Waiting for IAM role to propagate
   timeout /t 8 /nobreak > NUL
)
ECHO Creating Config ConfigurationRecorder
aws configservice put-configuration-recorder --configuration-recorder name=default,roleARN="arn:aws:iam::!ACCOUNT_ID!:role/config-role" --recording-group "{\"allSupported\":true,\"includeGlobalResourceTypes\":true}"
ECHO Creating Config DeliveryChannel
aws configservice put-delivery-channel --delivery-channel "{\"name\": \"default\",\"s3BucketName\": \"!BUCKET_NAME!\",\"configSnapshotDeliveryProperties\":{\"deliveryFrequency\": \"Six_Hours\"}}"
ECHO Config Resources Created
