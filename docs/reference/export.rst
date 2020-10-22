Export
------

.. argparse::
   :module: rdk
   :func: get_export_parser
   :prog: rdk export
   :nodescription:

   This command will export the specified Rule(s) to the terraform file, it supports the terraform versions 0.11 and 0.12.

   
   The ``--format`` flag can be used to specify export format, currently it supports only terraform. 
   The ``--version`` flag can be used to specify the terraform version.
   The ``--rdklib-layer-arn`` flag can be used for attaching Lambda Layer ARN that contains the desired rdklib.  Note that Lambda Layers are region-specific.
   The ``--lambda-role-arn`` flag can be used for assigning existing iam role to all Lambda functions created for Custom Config Rules.
   The ``--lambda-layers`` flag can be used for attaching a comma-separated list of Lambda Layer ARNs to deploy with your Lambda function(s).
   The ``--lambda-subnets`` flag can be used for attaching a comma-separated list of Subnets to deploy your Lambda function(s).
   The ``--lambda-security-groups`` flag can be used for attaching a comma-separated list of Security Groups to deploy with your Lambda function(s).
   The ``--lambda-timeout`` flag can be used for specifying the timeout associated to the lambda function

   