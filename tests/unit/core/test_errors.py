import rdk.core.errors as rdk_errors


def test_errors_hierarchy():
    assert issubclass(rdk_errors.RdkError, Exception)

    assert issubclass(rdk_errors.RdkAwsAccountInvalidError, rdk_errors.RdkError)
    assert issubclass(rdk_errors.RdkAwsRegionNotSetError, rdk_errors.RdkError)
    assert issubclass(rdk_errors.RdkAwsS3GetObjectError, rdk_errors.RdkError)
    assert issubclass(rdk_errors.RdkAwsS3UploadObjectError, rdk_errors.RdkError)
    assert issubclass(rdk_errors.RdkAwsS3DeleteObjectError, rdk_errors.RdkError)

    assert issubclass(rdk_errors.RdkCommandInvokeError, rdk_errors.RdkError)
    assert issubclass(rdk_errors.RdkCommandExecutionError, rdk_errors.RdkError)
    assert issubclass(rdk_errors.RdkCommandNotAllowedError, rdk_errors.RdkError)

    assert issubclass(rdk_errors.RdkCustodianPolicyReadError, rdk_errors.RdkError)
    assert issubclass(
        rdk_errors.RdkCustodianUnsupportedModeError, rdk_errors.RdkError
    )
    assert issubclass(
        rdk_errors.RdkCustodianLambdaMonitorError, rdk_errors.RdkError
    )
    assert issubclass(rdk_errors.RdkCustodianLambdaInvokeError, rdk_errors.RdkError)

    assert issubclass(rdk_errors.RdkMalformedPlanFile, rdk_errors.RdkError)
    assert issubclass(rdk_errors.RdkPyTestFixtureInitError, rdk_errors.RdkError)

    assert issubclass(rdk_errors.RdkTerraformMalformedPlanData, rdk_errors.RdkError)
    assert issubclass(
        rdk_errors.RdkTerraformMalformedStateData, rdk_errors.RdkError
    )
    assert issubclass(
        rdk_errors.RdkTerraformAvenueDownloadError, rdk_errors.RdkError
    )

    assert issubclass(
        rdk_errors.RdkReportUploadInvalidEnvironmentError, rdk_errors.RdkError
    )
    assert issubclass(rdk_errors.RdkReportUploadS3Error, rdk_errors.RdkError)
