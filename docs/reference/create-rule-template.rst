Create-Rule-Template
--------------------

.. argparse::
   :module: rdk
   :func: get_create_rule_template_parser
   :prog: rdk create-rule-template
   :nodescription:

   Generates and saves to a file a single CloudFormation template that can be used to deploy the specified Rule(s) into any account.  This feature has two primary uses:

   - Multi-account Config setup in which the Lambda Functions for custom Rules are deployed into a centralized "security" or "compliance" account and the Config Rules themselves are deployed into "application" or "satellite" accounts.
   - Combine many Config Rules into a single CloudFormation template for easier atomic deployment and management.

   The generated CloudFormation template includes a Parameter for the AccountID that contains the Lambda functions that provide the compliance logic for the Rules, and also exposes all of the Config Rule input parameters as CloudFormation stack parameters.

   By default the generated CloudFormation template will set up Config as per the settings used by the RDK ``init`` command, but those resources can be omitted using the ``--rules-only`` flag.

   The ``--config-role-arn`` flag can be used for assigning existing config role to the created Configuration Recorder.
   The ``-t | --tag-config-rules-script <file path>`` can now be used for output the script generated for create tags for each config rule.

   As of version 0.6, RDK supports Config remediation.  Note that in order to use SSM documents for remediation you must supply all of the necessary document parameters.  These can be found in the SSM document listing on the AWS console, but RDK will *not* validate at rule creation that you have all of the necessary parameters supplied.