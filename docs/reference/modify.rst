Modify
------

.. argparse::
   :module: rdk
   :func: get_modify_parser
   :prog: rdk modify
   :nodescription:

   Used to modify the local metadata for Config Rules created by the RDK.  This command takes the same arguments as the ``create`` command (all of them optional), and overwrites the Rule metadata for any flag specified.  Changes made using ``modify`` are not automatically pushed out to your AWS Account, and must be deployed as usual using the ``deploy`` command.
