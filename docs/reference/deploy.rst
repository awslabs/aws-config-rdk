Deploy
------

.. argparse::
   :module: rdk
   :func: get_deploy_parser
   :prog: rdk deploy
   :nodescription:

   This command will deploy the specified Rule(s) to the Account and Region determined by the credentials being used to execute the command, and the value of the AWS_DEFAULT_REGION environment variable, unless those credentials or region are overrided using the common flags.

   Once deployed, RDK will _not_ explicitly start a Rule evaluation.  Depending on the changes being made to your Config Rule setup AWS Config may re-evaluate the deployed Rules automatically, or you can run an evaluation using the AWS configservice CLI.

   The ``--functions-only`` flag can be used as part of a multi-account deployment strategy to push _only_ the Lambda functions (and necessary Roles and Permssions) to the target account.  This is intended to be used in conjunction with the ``create-rule-template`` command in order to separate the compliance logic from the evaluated accounts.  For an example of how this looks in practice, check out the `AWS Compliance-as-Code Engine <https://github.com/awslabs/aws-config-engine-for-compliance-as-code/>`_.
