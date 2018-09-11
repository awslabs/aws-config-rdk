Create-Rule-Template
--------------------

.. argparse::
   :module: rdk
   :func: get_create_rule_template_parser
   :prog: rdk create-rule-template
   :nodescription:

   Generates and saves to a file a single CloudFormation template that can be used to deploy the specified Rule(s) into any account.  This feature has two primary uses:

   - Multi-account Config setup in which the Lambda Functions for custom Rules are deployed into a centralized "securtiy" or "compliance" account and the Config Rules themselves are deployed into "application" or "satellite" accounts.
   - Combine many Config Rules into a single CloudFormation template for easier atomic deployment and management.

   The generated CloudFormation template includes a Parameter for the AccountID that contains the Lambda functions that provide the compliance logic for the Rules, and also exposes all of the Config Rule input parameters as CloudFormation stack parameters.

   By default the generated CloudFormation template will set up Config as per the settings used by the RDK ``init`` command, but those resources can be omitted using the ``--rules-only`` flag.
