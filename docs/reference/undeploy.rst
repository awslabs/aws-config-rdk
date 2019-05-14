Undeploy
--------

.. argparse::
   :module: rdk
   :func: get_undeploy_parser
   :prog: rdk undeploy
   :nodescription:

   The inverse of ``deploy``, this command is used to remove a Config Rule and its Lambda Function from the targeted account.

   This is intended to be used primarily for clean-up for testing deployment automation (perhaps from a CI/CD pipeline) to ensure that it works from an empty account, or to clean up a test account during development.  See also the `clean <./clean.html>`_ command if you want to more thoroughly scrub Config from your account.
