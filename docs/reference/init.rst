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

   Advanced Options:

   - ``--config-bucket-exists-in-another-account``: [optional] If the bucket being used by a Config Delivery Channel exists in another account, it is possible to skip the check that the bucket exists. This is useful when using ``init`` to initialize AWS Config in an account which already has a delivery channel setup with a central bucket. Currently, the rdk lists out all the buckets within the account your are running ``init`` from, to check if the provided bucket name exists, if it doesn't then it will create it. This presents an issue when a Config Delivery Channel has been configured to push configuration recordings to a central bucket. The bucket will never be found as it doesn't exist in the same account, but cannot be created as bucket names have to be globally unique.
   - ``--skip-code-bucket-creation``: [optional] If you want to use custom code bucket for rdk, enable this and use flag ``--custom-code-bucket`` to ``rdk deploy``
   - ``control-tower``: [optional] If your account is part of an AWS Control Tower setup --control-tower will skip the setup of configuration_recorder and delivery_channel