# Export

This command will export the specified Rule(s) to Terraform.

It supports Terraform version 1.x (older version support is deprecated).

# Arguments

- The `--format` flag can be used to specify export format, currently it supports only Terraform.
- The `--output-version` flag can be used to specify the Terraform version. Currently, only "1.x" is supported.
- The `--rdklib-layer-arn` flag can be used for attaching Lambda Layer ARN that contains the desired `rdklib` layer. Note that Lambda Layers are region-specific.
- The `--lambda-role-arn` flag can be used for assigning existing iam role to all Lambda functions created for Custom Config Rules.
- The `--lambda-layers` flag can be used for attaching a comma-separated list of Lambda Layer ARNs to deploy with your Lambda function(s).
- The `--lambda-subnets` flag can be used for attaching a comma-separated list of Subnets to deploy your Lambda function(s).
- The `--lambda-security-groups` flag can be used for attaching a comma-separated list of Security Groups to deploy with your Lambda function(s).
- The `--lambda-timeout` flag can be used for specifying the timeout associated to the lambda function
