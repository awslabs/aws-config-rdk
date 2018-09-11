Sample-CI
---------

.. argparse::
   :module: rdk
   :func: get_sample_ci_parser
   :prog: rdk sample-ci
   :nodescription:

   This utility command outputs a sample Configuration Item for the specified resource type.  This can be useful when writing new custom Config Rules to help developers know what the CI structure and plausible values for the resource type are.

   Note that you can construct Config Evaluations for any resource type that is supported by CloudFormation, however you can not create change-triggered Config Rules for resource types not explicitly supported by Config, and some of the console functionality in AWS Config may be limited.

   `CFN-supported resources  <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-supported-resources.html>`_
   `Config-supported resources <https://docs.aws.amazon.com/config/latest/developerguide/resource-config-reference.html>`_

   ci_type : @replace
      One of the supported Config-supported resource types.
