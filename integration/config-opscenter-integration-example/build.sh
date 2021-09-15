#!/usr/bin/env bash


aws cloudformation deploy --stack-name my-opsitem-role \
--template-file opsitem-role.yaml \
--capabilities CAPABILITY_IAM

aws cloudformation deploy --stack-name my-config-rule \
--template-file s3EncryptedConfigRule.yaml