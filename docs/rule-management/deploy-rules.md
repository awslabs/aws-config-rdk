# Deploy Rule

Once you have completed your compliance validation code and set your
Rule's configuration, you can deploy the Rule to your account using the
`deploy` command. This will zip up your code (and the other associated
code files, if any) into a deployable package (or run a gradle build if
you have selected the java8 runtime or run the Lambda packaging step
from the dotnet CLI if you have selected the dotnetcore1.0 runtime),
copy that zip file to S3, and then launch or update a CloudFormation
stack that defines your Config Rule, Lambda function, and the necessary
permissions and IAM Roles for it to function. Since CloudFormation does
not deeply inspect Lambda code objects in S3 to construct its changeset,
the `deploy` command will also directly update the Lambda function for
any subsequent deployments to make sure code changes are propagated
correctly.

```bash
rdk deploy MyRule
Running deploy!
Zipping MyRule
Uploading MyRule
Creating CloudFormation Stack for MyRule
Waiting for CloudFormation stack operation to complete...
...
Waiting for CloudFormation stack operation to complete...
Config deploy complete.
```

The exact output will vary depending on Lambda runtime. You can use the
`--all` flag to deploy all of the rules in your working directory. If
you used the `--generate-lambda-layer` flag in rdk init, use the
`--generated-lambda-layer` flag for rdk deploy.

## Deploy Organization Rule

You can also deploy the Rule to your AWS Organization using the
`deploy-organization` command. For successful evaluation of custom rules
in child accounts, please make sure you do one of the following:

1. Set ASSUME_ROLE_MODE in Lambda code to True, to get the Lambda to assume the Role attached on the Config Service and confirm that the role trusts the master account where the Lambda function is going to be deployed.
2. Set ASSUME_ROLE_MODE in Lambda code to True, to get the Lambda to assume a custom role and define an optional parameter with key as ExecutionRoleName and set the value to your custom role name; confirm that the role trusts the master account of the organization where the Lambda function will be deployed.

```bash
rdk deploy-organization MyRule
Running deploy!
Zipping MyRule
Uploading MyRule
Creating CloudFormation Stack for MyRule
Waiting for CloudFormation stack operation to complete...
...
Waiting for CloudFormation stack operation to complete...
Config deploy complete.
```

The exact output will vary depending on Lambda runtime. You can use the
`--all` flag to deploy all of the rules in your working directory. This
command uses `PutOrganizationConfigRule` API for the rule deployment. If
a new account joins an organization, the rule is deployed to that
account. When an account leaves an organization, the rule is removed.
Deployment of existing organizational AWS Config Rules will only be
retried for 7 hours after an account is added to your organization if a
recorder is not available. You are expected to create a recorder if one
doesn't exist within 7 hours of adding an account to your organization.

## View Logs For Deployed Rule

Once the Rule has been deployed to AWS you can get the CloudWatch logs
associated with your Lambda function using the `logs` command.

```bash
rdk logs MyRule -n 5
2017-11-15 22:59:33 - START RequestId: 96e7639a-ca15-11e7-95a2-b1521890638d Version: $LATEST
2017-11-15 23:41:13 - REPORT RequestId: 68e0304f-ca1b-11e7-b735-81ebae95acda    Duration: 0.50 ms    Billed Duration: 100 ms     Memory Size: 256 MB     Max Memory Used: 36 MB
2017-11-15 23:41:13 - END RequestId: 68e0304f-ca1b-11e7-b735-81ebae95acda
2017-11-15 23:41:13 - Default RDK utility class does not yet support Scheduled Notifications.
2017-11-15 23:41:13 - START RequestId: 68e0304f-ca1b-11e7-b735-81ebae95acda Version: $LATEST
```

You can use the `-n` and `-f` command line flags just like the UNIX
`tail` command to view a larger number of log events and to continuously
poll for new events. The latter option can be useful in conjunction with
manually initiating Config Evaluations for your deploy Config Rule to
make sure it is behaving as expected.
