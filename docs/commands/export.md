# Export

This command will export the specified Rule(s) to Terraform (1.x and later) manifest(s).

In order to reduce repeated code, the exported rule will reference a source module, by default `../rdk_module` (or `../rdk_organization_module` for Org Config rules). Running `rdk export` will create `rdk_module` in the current working directory if it does not exist already, by copying RDK's version of the module from `rdk/template/terraform/1.x/rdk_module`.

## Example Usage - Terraform

```bash
# assume your cwd is the parent of `my_rule`
#  my_rule
#  ├──parameters.json
#  ├──rule.py
#  └──rule_test.py
TF_STATE_BUCKET=my-bucket
rdk export my_rule --backend-bucket $TF_STATE_BUCKET # Creates a TF manifest and backend manifest in the my_rule folder
terraform plan
```

## Example Usage - Terragrunt

The intended usage in CI/CD pipelines looks something like this -- Terragrunt here is useful to run changes in subfolders:
```bash
# Assuming a folder of rules, with one subfolder per rule, containing:
#  parameters.json
#  rule.py
#  rule_test.py

TF_STATE_BUCKET=my-bucket
rdk export -a --add-terragrunt-file --backend-bucket $TF_STATE_BUCKET # Creates a TF manifest, terragrunt placeholder file, and backend manifest in ALL rule folders in your current directory
terragrunt run-all apply
```

# Arguments

- The `--format` flag can be used to specify export format, currently it supports only `terraform`.
- The `--output-version` flag can be used to specify the Terraform major version. Currently, only `1.x` is supported.
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