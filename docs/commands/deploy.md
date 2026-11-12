# Deploy

This command will deploy the specified Rule(s) to the Account and Region
determined by the credentials being used to execute the command, and the
value of the AWS_DEFAULT_REGION environment variable, unless those
credentials or region are overridden using the common flags.

Once deployed, RDK will **not** explicitly start a Rule evaluation.
Depending on the changes being made to your Config Rule setup AWS Config
may re-evaluate the deployed Rules automatically, or you can run an
evaluation using the AWS configservice CLI.

The `--functions-only` flag can be used as part of a multi-account
deployment strategy to push **only** the Lambda functions (and
necessary Roles and Permssions) to the target account. This is intended
to be used in conjunction with the `create-rule-template` command in
order to separate the compliance logic from the evaluated accounts. For
an example of how this looks in practice, check out the [AWS
Compliance-as-Code
Engine](https://github.com/awslabs/aws-config-engine-for-compliance-as-code/).
The `--rdklib-layer-arn` flag can be used for attaching Lambda Layer ARN
that contains the desired rdklib. Note that Lambda Layers are
region-specific. The `--lambda-role-arn` flag can be used for assigning
existing iam role to all Lambda functions created for Custom Config
Rules. The `--lambda-layers` flag can be used for attaching a
comma-separated list of Lambda Layer ARNs to deploy with your Lambda
function(s). The `--lambda-subnets` flag can be used for attaching a
comma-separated list of Subnets to deploy your Lambda function(s). The
`--lambda-security-groups` flag can be used for attaching a
comma-separated list of Security Groups to deploy with your Lambda
function(s). The `--custom-code-bucket` flag can be used for providing
the custom code S3 bucket name, which is not created with rdk init, for
generated cloudformation template storage. The `--boundary-policy-arn`
flag can be used for attaching boundary Policy ARN that will be added to
rdkLambdaRole. The `--lambda-timeout` flag can be used for specifying
the timeout associated to the lambda function

## Code bucket ownership check

As of version `2.0.0`, every S3 write RDK performs against the code
bucket (Lambda code zips and the `--functions-only` CloudFormation
template) includes the `ExpectedBucketOwner` parameter set to the
account ID of the credentials running `rdk`. If the bucket is owned by
any other account, S3 rejects the request with `403 Access Denied` and
nothing is uploaded.

This protects against *bucket squatting*: the default code bucket name
(`config-rule-code-bucket-<account-id>-<region>`) is predictable, so a
third party could pre-create it in their own account and receive your
rule code, or serve modified code to your Lambda functions.

The `--skip-bucket-ownership-check` flag disables this check. It is
intended **only** for the case where `--custom-code-bucket` points at a
bucket that is deliberately owned by a different account, for example a
central artifact bucket in a shared-services account whose bucket policy
grants your deployment role `s3:PutObject` (and grants Lambda/CloudFormation
read access). Note that Lambda requires the bucket to be in the same
Region as the function.

```bash
rdk deploy MyRule --custom-code-bucket my-central-artifacts-us-east-1 --skip-bucket-ownership-check
```

- The flag is rejected if `--custom-code-bucket` is not also supplied;
  the default code bucket is always ownership-checked.
- RDK logs a warning whenever the check is skipped.
- Only use the flag with a bucket name you control or trust. With the
  check disabled, RDK cannot detect a bucket that has been created by an
  unexpected account.

**Upgrading from 1.x:** if you deploy with a `--custom-code-bucket` owned
by another account, add `--skip-bucket-ownership-check` to your `rdk
deploy` / `rdk deploy-organization` commands. No change is needed if your
code bucket is owned by the deploying account (including the default
bucket created by `rdk init`).

The same flag is available on `rdk deploy-organization`.

Note: Behind the scenes the `--functions-only` flag generates a
CloudFormation template and runs a \"create\" or \"update\" on the
targeted AWS Account and Region. If subsequent calls to `deploy` with
the `--functions-only` flag are made with the same stack name (either
the default or otherwise) but with *different Config rules targeted*,
any Rules deployed in previous `deploy`s but not included in the latest
`deploy` will be removed. After a functions-only `deploy` **only** the
Rules specifically targeted by that command (either through Rulesets or
an explicit list supplied on the command line) will be deployed in the
environment, all others will be removed.s
