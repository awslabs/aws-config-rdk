"""
Well-known exceptions raised by Rdk.
"""


class RdkError(Exception):
    """
    Base class for all Rdk errors.
    """


class RdkAwsAccountInvalidError(RdkError):
    """
    Current set of AWS Credentials belongs to an unsupported AWS Account.
    """


class RdkAwsRegionNotSetError(RdkError):
    """
    Current AWS Region was not determined.
    """


class RdkAwsS3GetObjectError(RdkError):
    """
    Error occured when fetching from S3.
    """


class RdkAwsS3UploadObjectError(RdkError):
    """
    Error occured when uploading to S3.
    """


class RdkAwsS3DeleteObjectError(RdkError):
    """
    Error occured when deleting an S3 object.
    """


class RdkCommandInvokeError(RdkError):
    """
    Error occured when invoking a command.
    """


class RdkCommandExecutionError(RdkError):
    """
    Error occured when executing a command.
    """


class RdkCommandNotAllowedError(RdkError):
    """
    An unsupported command was requested to be executed.
    """


class RdkCustodianPolicyReadError(RdkError):
    """
    Error reading a custodian policy.
    """


class RdkCustodianUnsupportedModeError(RdkError):
    """
    Custodian policy is using an unsupported mode.
    """


class RdkCustodianLambdaMonitorError(RdkError):
    """
    Error when monitoring Custodian-managed Lambda Functions.
    """


class RdkCustodianActionWaiterError(RdkError):
    """
    Error when implementing wait for custodian actions.
    """


class RdkCustodianLambdaInvokeError(RdkError):
    """
    Error when invoking Custodian-managed Lambda Functions.
    """


class RdkMalformedPlanFile(RdkError):
    """
    Malformed Rdk Test Plan File.
    """


class RdkPyTestFixtureInitError(RdkError):
    """
    Error initializing RdkPyTestFixture.
    """


class RdkTestExecutionError(RdkError):
    """
    Error while executing Rdk test case.
    """


class RdkTerraformMalformedPlanData(RdkError):
    """
    Malformed Terraform JSON Plan-Representation.
    """


class RdkTerraformMalformedStateData(RdkError):
    """
    Malformed Terraform JSON State-Representation.
    """


class RdkTerraformAvenueDownloadError(RdkError):
    """
    Error downloading terraform-avenue provider.
    """


class RdkReportUploadS3Error(RdkError):
    """
    Error uploading a test report to S3.
    """


class RdkReportUploadInvalidEnvironmentError(RdkError):
    """
    Invalid Report Upload Environment.
    """
