Test-Local
----------

.. argparse::
   :module: rdk
   :func: get_test_local_parser
   :prog: rdk test-local
   :nodescription:

   Shorthand command for running the unit tests defined for Config Rules that use a Python runtime.  When a Python 3.6+ Rule is created using the ``create`` command a unit test template is created in the Rule directory.  This test boilerplate includes minimal tests, as well as a framework for using the ``unittest.mock`` library for stubbing out Boto3 calls.  This allows more sophisticated test cases to be written for Periodic rules that need to make API calls to gather information about the environment.
