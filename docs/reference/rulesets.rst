Rulesets
--------

.. argparse::
   :module: rdk
   :func: get_rulesets_parser
   :prog: rdk rulesets
   :nodescription:

   Rulesets provide a mechanism to tag individual Config Rules into groups that can be acted on as a unit.  Ruleset tags are single keywords, and the commands ``deploy``, ``create-rule-template``, and ``undeploy`` can all expand Ruleset parameters and operate on the resulting list of Rules.

   The most common use-case for Rulesets is to define standardized Account metadata or data classifications, and then tag individual Rules to all of the appropriate metadata tags or classification levels.

   Example: If you have Account classifications of "Public", "Private", and "Restricted" you can tag all of your Rules as "Restricted", and a subset of them that deal with private network security as "Private".  Then when you need to deploy controls to a new "Private" account you can simply use ``rdk create-rule-template --rulesets Private`` to generate a CloudFormation template that includes all of the Rules necessary for your "Private" classification, but omit the Rules that are only necessary for "Restricted" accounts.  Additionally, as your compliance requirements change and you add Config Rules you can tag them as appropriate, re-generate your CloudFormation templates, and re-deploy to make sure your Accounts are all up-to-date.

   You may also choose to classify accounts using binary attributes ("Prod" vs. "Non-Prod" or "PCI" vs. "Non-PCI"), and then generate account-specific CloudFormation templates using the Account metadata to ensure that the appropriate controls are deployed.
