Logs
----

.. argparse::
   :module: rdk
   :func: get_logs_parser
   :prog: rdk logs
   :nodescription:

   The ``logs`` command provides a shortcut to accessing the CloudWatch Logs output from the Lambda Functions that back your custom Config Rules.  Logs are displayed in chronological order going back the number of log entries specified by the ``--number`` flag (default 3). It supports a ``--follow`` flag similar to the UNIX command ``tail`` so that you can choose to continually poll CloudWatch to deliver new log items as they are delivered by your Lambda function.

   In addition to any output that your function emits via ``print()`` or ``console.log()`` commands, Lambda will also record log lines for the start and stop of each Lambda invocation, including the runtime and memory usage.
