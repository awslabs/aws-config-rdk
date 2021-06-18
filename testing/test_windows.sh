#!/bin/bash

#Params
#python_version must be "3"
python_version=$1

echo $CODEBUILD_SOURCE_VERSION
if [[ $CODEBUILD_SOURCE_VERSION =~ MyApp\/(.*).zip ]]; then
  echo ${BASH_REMATCH[1]};
  build_id=${BASH_REMATCH[1]};

  version_string="Python36";
  windows_ami="ami-574d182b"

  if [[ ${python_version} == "3" ]]; then
    version_string="Python36";
  elif [[ ${python_version} == "37" ]]; then
    version_string="Python37";
  elif [[ ${python_version} == "38" ]]; then
    version_string="Python38";
  fi

  #Construct powershell script to run test and publish results to S3
  user_data="
    <powershell>
    Copy-S3Object -BucketName rdk-testing-source-bucket -KeyPrefix ${build_id} -LocalFolder C:\tmp
    python -m pip install C:\tmp
    set AWS_DEFAULT_REGION=ap-southeast-1
    Set-DefaultAWSRegion -Region ap-southeast-1
    python C:\\${version_string}\Scripts\rdk --region ap-southeast-1 init >C:\tmp\output.txt
    python C:\\${version_string}\Scripts\rdk --region ap-southeast-1 create WP${python_version}-TestRule-P38 --runtime python3.8 --resource-types AWS::EC2::SecurityGroups >>C:\tmp\output.txt
    python C:\\${version_string}\Scripts\rdk --region ap-southeast-1 create WP${python_version}-TestRule-P37 --runtime python3.7 --resource-types AWS::EC2::SecurityGroups >>C:\tmp\output.txt
    python C:\\${version_string}\Scripts\rdk --region ap-southeast-1 create WP${python_version}-TestRule-P3 --runtime python3.6 --resource-types AWS::EC2::SecurityGroups >>C:\tmp\output.txt
    python C:\\${version_string}\Scripts\rdk --region ap-southeast-1 create WP${python_version}-TestRule_JS --runtime nodejs4.3 --resource-types AWS::EC2::SecurityGroups >>C:\tmp\output.txt
    python C:\\${version_string}\Scripts\rdk --region ap-southeast-1 modify WP${python_version}-TestRule-P3 --input-parameters '{\"TestParameter\":\"TestValue\"}' >>C:\tmp\output.txt
    python C:\\${version_string}\Scripts\rdk --region ap-southeast-1 create WP${python_version}-TestRule_P3 --runtime python3.6 --maximum-frequency One_Hour >>C:\tmp\output.txt
    python C:\\${version_string}\Scripts\rdk --region ap-southeast-1 test-local WP${python_version}-TestRule-P3  >>C:\tmp\output.txt
    python C:\\${version_string}\Scripts\rdk --region ap-southeast-1 deploy WP${python_version}-TestRule-P3 >>C:\tmp\output.txt
    Start-Sleep -s 60
    python C:\\${version_string}\Scripts\rdk --region ap-southeast-1 logs WP${python_version}-TestRule-P3 >>C:\tmp\output.txt
    type C:\tmp\output.txt
    Write-S3Object -BucketName rdk-testing-windows-results -File C:\tmp\output.txt -Key ${build_id}/${version_string}Output.txt
    </powershell>
  "
  echo "${user_data}"


  #Launch EC2 instance from specified AMI to run test script via UserData
  aws ec2 run-instances --image-id ${windows_ami} --instance-type t2.small --security-group-ids sg-4e5ef137 --subnet-id subnet-aa094fcd --iam-instance-profile Arn=arn:aws:iam::711761543063:instance-profile/WindowsBuildServer --user-data "${user_data}" --key-name WindowsBuild --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=WindowsRDKTest}]'

  #Wait for output file to show up in S3, or for timeout.
  file_found=0
  while [ ${file_found} -ne 1 ]; do
    aws s3 ls s3://rdk-testing-windows-results/${build_id}/${version_string}Output.txt
    if [[ $? -ne 0 ]]; then
      echo "Waiting for output file in S3";
      sleep 10;
    else
      file_found=1
      aws s3 cp s3://rdk-testing-windows-results/${build_id}/${version_string}Output.txt output.txt
    fi
  done

  #Terminate build instance
  aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId]' --filters 'Name=tag-value,Values=WindowsRDKTest' --output text |
  while read line;
  do aws ec2 terminate-instances --instance-ids $line
  done

  #return success or failure.
  cat ./output.txt
fi
