Deploy
------

.. argparse::
   :module: rdk
   :func: get_deploy_parser
   :prog: rdk deploy
   :nodescription:

   This command will deploy the specified Rule(s) to the Account and Region determined by the credentials being used to execute the command, and the value of the AWS_DEFAULT_REGION environment variable, unless those credentials or region are overridden using the common flags.

   Once deployed, RDK will _not_ explicitly start a Rule evaluation.  Depending on the changes being made to your Config Rule setup AWS Config may re-evaluate the deployed Rules automatically, or you can run an evaluation using the AWS configservice CLI.

   The ``--functions-only`` flag can be used as part of a multi-account deployment strategy to push _only_ the Lambda functions (and necessary Roles and Permssions) to the target account.  This is intended to be used in conjunction with the ``create-rule-template`` command in order to separate the compliance logic from the evaluated accounts.  For an example of how this looks in practice, check out the `AWS Compliance-as-Code Engine <https://github.com/awslabs/aws-config-engine-for-compliance-as-code/>`_.
   The ``--rdklib-layer-arn`` flag can be used for attaching Lambda Layer ARN that contains the desired rdklib.  Note that Lambda Layers are region-specific.
   The ``--lambda-role-arn`` flag can be used for assigning existing iam role to all Lambda functions created for Custom Config Rules.
   The ``--lambda-layers`` flag can be used for attaching a comma-separated list of Lambda Layer ARNs to deploy with your Lambda function(s).
   The ``--lambda-subnets`` flag can be used for attaching a comma-separated list of Subnets to deploy your Lambda function(s).
   The ``--lambda-security-groups`` flag can be used for attaching a comma-separated list of Security Groups to deploy with your Lambda function(s).
   The ``--custom-code-bucket`` flag can be used for providing the custom code S3 bucket name, which is not created with rdk init, for generated cloudformation template storage.
   The ``--boundary-policy-arn`` flag can be used for attaching boundary Policy ARN that will be added to rdkLambdaRole.
   The ``--lambda-timeout`` flag can be used for specifying the timeout associated to the lambda function


   Note: Behind the scenes the ``--functions-only`` flag generates a CloudFormation template and runs a "create" or "update" on the targeted AWS Account and Region.  If subsequent calls to ``deploy`` with the ``--functions-only`` flag are made with the same stack name (either the default or otherwise) but with *different Config rules targeted*, any Rules deployed in previous ``deploy``s but not included in the latest ``deploy`` will be removed.  After a functions-only ``deploy`` _only_ the Rules specifically targeted by that command (either through Rulesets or an explicit list supplied on the command line) will be deployed in the environment, all others will be removed.s
