# Export

This command will export the specified Rule(s) to Terraform (1.x and later) manifest(s).

The `export` command will create a Terraform manifest file per rule (eg. `myrule.tf`) and place it in a `terraform_rdk_rules` folder, over-writing any TF file of the same name. Setting the `--output-version` argument to `1.x_organization` will export the selected rules into Terraform manifests with Organization-wide Config rules.

In order to reduce repeated code, the exported rule will reference a source module, by default `./rdk_module` (or `./rdk_organization_module` for Org Config rules). Running `rdk export` will create `rdk_module` in the `terraform_rdk_rules` directory if it does not exist already, by copying RDK's version of the module from `rdk/template/terraform/1.x/rdk_module` (or `rdk_organization_module` where relevant).

Users can also specify `--backend-bucket` and `--add-provider-manifest` to create `backend.tf` and `provider.tf` files in these repositories, with opinionated defaults. This should only be needed once.

## Example Usage - Single Rule

```bash
cd rdk_source
#  rdk_source
#  └─my_rule
#    ├──parameters.json
#    ├──rule.py
#    └──rule_test.py
TF_STATE_BUCKET=my-bucket
rdk export my_rule # Creates a TF manifest and adds it to the terraform_rdk_rules folder
cd terraform_rdk_rules
terraform plan
```

## Example Usage - All Rules

```bash
# assume your cwd is the parent folder of many RDK rules.
cd rdk_source
TF_STATE_BUCKET=my-bucket
REGION=us-west-2
# You could run this manually and commit it or include `rdk export` as a step in a CI/CD pipeline.
rdk --region $REGION export -a --organization-rule --backend-bucket-name $TF_STATE_BUCKET --add-provider-manifest # Creates a TF manifest for each rule in the directory and adds to terraform_rdk_rules. The TF manifests will all use the aws_config_organization_custom_rule resouce. Also adds a backend and provider manifest to terraform_rdk_rules.
cd terraform_rdk_rules
terraform plan
```

# Arguments

- The `--format` flag can be used to specify export format, though currently it supports only (and defaults to) `terraform`.
- The `--output-version` flag can be used to specify the Terraform major version. Currently, only `1.x` or `1.x_organization` (for Org rules) is supported.
- The `--rdklib-layer-arn` flag can be used for attaching Lambda Layer ARN that contains the desired `rdklib` layer. Note that Lambda Layers are region-specific.
- The `--lambda-role-arn` flag can be used for assigning existing iam role to all Lambda functions created for Custom Config Rules.
- The `--lambda-layers` flag can be used for attaching a comma-separated list of Lambda Layer ARNs to deploy with your Lambda function(s).
- The `--lambda-subnets` flag can be used for attaching a comma-separated list of Subnets to deploy your Lambda function(s).
- The `--lambda-security-groups` flag can be used for attaching a comma-separated list of Security Groups to deploy with your Lambda function(s).
- The `--lambda-timeout` flag can be used for specifying the timeout associated to the lambda function
- The `--copy-terraform-module` flag will copy the `rdk_module` folder into your rule directory.
- The `custom-module-source-location` flag will set the exported TF module invocation to be sourced from the location you specify. This is useful if you modify the module or want to source it from a central location. For example, you could pass the module call to a source that deploys an Config Organization rule. By default, it will point to `./rdk_module`.
- The `--backend-bucket-name` argument will create a `backend.tf` file in the `terraform_rdk_rules` directory, pointing to the specified backend S3 bucket. The key for the state file will be `rdk_modules/<rule name>`. 
- The `--add-provider-manifest` argument will create a `provider.tf` file in the `terraform_rdk_rules` directory, ensuring that the rules are deployed in the right region. `export` does not currently natively support multi-region deployment.
