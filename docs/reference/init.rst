Init
----

.. argparse::
   :module: rdk
   :func: get_init_parser
   :prog: rdk init
   :nodescription:

   Sets up the AWS Config Service in an AWS Account. This includes:

   - Config Configuration Recorder
   - Config Delivery Channel
   - IAM Role for Delivery Channel
   - S3 Bucket for Configuration Snapshots
   - S3 Bucket for Lambda Code

   Additionally, ``init`` will make sure that the Configuration Recorder is on and functioning, that the Delivery Channel has the appropriate Role attached, and that the Delivery Channel Role has the proper permissions.

   Note: Even without Config Rules running the Configuration Recorder is still capturing Configuration Item snapshots and storing them in S3, so running ``init`` will incur AWS charges!

   Also Note: AWS Config is a regional service, so running ``init`` will only set up Config in the region currently specified in your AWS_DEFAULT_REGION environment variable or in the ``--region`` flag.
