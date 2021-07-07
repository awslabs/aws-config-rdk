#!/usr/bin/env bash


aws cloudformation delete-stack --stack-name my-opsitem-role
aws cloudformation delete-stack --stack-name my-config-rule