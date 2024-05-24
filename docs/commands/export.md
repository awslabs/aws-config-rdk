# Export

This command will export the specified Rule(s) to Terraform.

It supports Terraform version 1.x (older TF version support is deprecated).

In order to reduce repeated code, the 1.x Terraform export will generate a module invocation that passes appropriate arguments to the source module.

The source module will live in `rdk/template/terraform/1.x/rdk_module` and will be exported by default (though you can also point it to a different module folder if you want to reduce repeated code).

The intended usage in CI/CD pipelines looks something like this:
```bash
# Assuming a folder of rules, with one subfolder per rule, containing:
#  parameters.json
#  rule.py
#  rule_test.py

TF_STATE_BUCKET=my-bucket
rdk export -a --add-terragrunt-file --backend-bucket $TF_STATE_BUCKET # Creates a TF manifest, terragrunt placeholder file, and backend in each rule folder in your rules directory
terragrunt run-all apply
```

# Arguments

- The `--format` flag can be used to specify export format, currently it supports only Terraform.
- The `--output-version` flag can be used to specify the Terraform version. Currently, only "1.x" is supported.
- The `--rdklib-layer-arn` flag can be used for attaching Lambda Layer ARN that contains the desired `rdklib` layer. Note that Lambda Layers are region-specific.
- The `--lambda-role-arn` flag can be used for assigning existing iam role to all Lambda functions created for Custom Config Rules.
- The `--lambda-layers` flag can be used for attaching a comma-separated list of Lambda Layer ARNs to deploy with your Lambda function(s).
- The `--lambda-subnets` flag can be used for attaching a comma-separated list of Subnets to deploy your Lambda function(s).
- The `--lambda-security-groups` flag can be used for attaching a comma-separated list of Security Groups to deploy with your Lambda function(s).
- The `--lambda-timeout` flag can be used for specifying the timeout associated to the lambda function
- The `--copy-terraform-module` flag will copy the `rdk_module` folder into your rule directory.
- The `custom-module-source-location` flag will set the exported TF module invocation to be sourced from the location you specify. This is useful if you modify the module or want to source it from a central location. For example, you could pass the module call to a source that deploys an Config Organization rule.
- The `backend-bucket` flag will create a `backend.tf` file in the rule directory, pointing to the specified backend S3 bucket. The key for the state file will be `rdk_modules/<rule name>`. 
- The `add-terragrunt-file` flag will create a `terragrunt.hcl` file in the rule directory. This is used to indicate to `terragrunt` that the module should be included in `terragrunt` automations like `run-all`.