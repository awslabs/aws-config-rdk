#!/bin/bash

#Params
#python_version must be either "2" or "3"
python_version = $1

echo $CODEBUILD_SOURCE_VERSION
if [[ $CODEBUILD_SOURCE_VERSION =~ MyApp\/(.*).zip ]]; then
  echo ${BASH_REMATCH[1]};
  build_id=${BASH_REMATCH[1]};

  version_string = "Python27";
  windows_ami = "ami-995702e5"

  if [[ ${python_version} == "3" ]]; then
    version_string="Python36";
  fi

  #Get start time

  #Construct powershell script to run test and publish results to S3
  user_data="
    <powershell>
    Copy-S3Object -BucketName rdk-testing-source-bucket -KeyPrefix ${build_id} -LocalFolder C:/tmp
    arn:aws:s3:::rdk-testing-source-bucket
    ./python -m pip install C:\tmp
    set AWS_DEFAULT_REGION=ap-southeast-1
    python C:\${version_string}\Scripts\rdk init >C:\tmp\output.txt
    python C:\${version_string}\Scripts\rdk create WP${version}-TestRule-P3 --runtime python3.6 --resource-types AWS::EC2::SecurityGroups >>C:\tmp\output.txt
    python C:\${version_string}\Scripts\rdk create WP${version}-TestRule-P2 --runtime python2.7 --resource-types AWS::EC2::SecurityGroups >>C:\tmp\output.txt
    python C:\${version_string}\Scripts\rdk test-local --all >>C:\tmp\output.txt
    rdk deploy --all >>C:\tmp\output.txt
    Start-Sleep -s 30
    python C:\${version_string}\Scripts\rdk logs WP${version}-TestRule-P3 >>C:\tmp\output.txt
    Write-S3Object -BucketName rdk-testing-windows-results -File C:\tmp\${version_string}Output.txt -Key ${build_id}/${version_string}Output.txt
    </powershell>
  "

  #Launch EC2 instance from specified AMI to run test script via UserData
  aws ec2 run-instances --image-id ${windows_ami} --instance-type t2.small --security-group-ids sg-4e5ef137 --subnet-id subnet-aa094fcd --iam-instance-profile Arn=arn:aws:iam::711761543063:instance-profile/WindowsBuildServer,Name=WindowsBuildServer --user-data "${user_data}"

  #Wait for output file to show up in S3, or for timeout.
  file_found=0
  while [ ${file_found} -ne 1 ]; do
    aws s3 ls s3://rdk-testing-windows-results/${build_id}/${version_string}Output.txt
    if [[ $? -ne 0 ]]; then
      sleep 10;
    else
      file_found=1
      aws s3 cp s3://rdk-testing-windows-results/${build_id}/${version_string}Output.txt output.txt
    fi
  done
  
  #Terminate build instance and return success or failure.
  cat output.txt
fi
