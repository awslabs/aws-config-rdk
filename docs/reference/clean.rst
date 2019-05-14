Clean
-----

.. argparse::
   :module: rdk
   :func: get_clean_parser
   :prog: rdk clean
   :nodescription:

   The ``clean`` command is the inverse of the ``init`` command, and can be used to completely remove Config resources from an account, including the Configuration Recorder, Delivery Channel, S3 buckets, Roles, and Permissions.  This is useful for testing account provisioning automation and for running automated tests in a clean environment.
