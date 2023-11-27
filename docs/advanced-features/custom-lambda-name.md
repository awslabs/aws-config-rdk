# Custom Lambda Function Name

As of version 0.7.14, instead of defaulting the lambda function names to
`RDK-Rule-Function-<RULE_NAME>` it is possible to customize the name for
the Lambda function to any 64 characters string as per Lambda's naming
standards using the optional `--custom-lambda-name` flag while
performing `rdk create`. This opens up new features like :

1. Longer config rule name.
2. Custom lambda function naming as per personal or enterprise standards.

```bash
rdk create MyLongerRuleName --runtime python3.11 --resource-types AWS::EC2::Instance --custom-lambda-name custom-prefix-for-MyLongerRuleName
Running create!
Local Rule files created.
```

The above example would create files with config rule name as
`MyLongerRuleName` and lambda function with the name
`custom-prefix-for-MyLongerRuleName` instead of
`RDK-Rule-Function-MyLongerRuleName`
