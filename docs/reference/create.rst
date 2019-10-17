Create
------

.. argparse::
   :module: rdk
   :func: get_create_parser
   :prog: rdk create

   As of version 0.6, RDK supports Config remediation.  Note that in order to use SSM documents for remediation you must supply all of the necessary document parameters.  These can be found in the SSM document listing on the AWS console, but RDK will *not* validate at rule creation that you have all of the necessary parameters supplied.
   
