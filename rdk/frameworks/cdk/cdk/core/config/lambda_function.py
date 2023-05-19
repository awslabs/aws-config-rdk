import json
import boto3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from constructs import Construct
from aws_cdk import aws_lambda as lambda_

from ..errors import RdkParametersInvalidError

from ..rule_parameters import get_rule_name, rdk_supported_custom_rule_runtime


@dataclass
class LambdaFunction:
    """
    Defines Lambda Function.

    Parameters:

    * **`code`** (_Code_): The source code of your Lambda function. You can point to a file in an Amazon Simple Storage Service (Amazon S3) bucket or specify your source code as inline text.
    * **`handler`** (_str_): The name of the method within your code that Lambda calls to execute your function. The format includes the file name. It can also include namespaces and other qualifiers, depending on the runtime. For more information, see https://docs.aws.amazon.com/lambda/latest/dg/foundation-progmodel.html. Use Handler.FROM_IMAGE when defining a function from a Docker image. NOTE: If you specify your source code as inline text by specifying the ZipFile property within the Code property, specify index.function_name as the handler.
    * **`runtime`** (_Runtime_): The runtime environment for the Lambda function that you are uploading. For valid values, see the Runtime property in the AWS Lambda Developer Guide. Use Runtime.FROM_IMAGE when defining a function from a Docker image.
    * **`layers`** (_Optional[Sequence[ILayerVersion]]_): Optional - A list of layers to add to the function’s execution environment. You can configure your Lambda function to pull in additional code during initialization in the form of layers. Layers are packages of libraries or other dependencies that can be used by multiple functions. Default: - No layers.

    """

    code: lambda_.Code = field(init=False)
    handler: str = field(init=False)
    runtime: lambda_.Runtime = field(init=False)
    # layers: Optional[Sequence[lambda_.ILayerVersion]]

    # TODO: add support for more lambda configuration.

    def __init__(self, code: lambda_.Code, rule_parameters: dict):
        param = rule_parameters["Parameters"]
        self.code = code
        self.handler = f"{param['RuleName']}.lambda_handler"
        # self.layers = []
        if "SourceRuntime" in param:
            try:
                self.runtime = getattr(
                    lambda_.Runtime,
                    param["SourceRuntime"]
                    .replace("-lib", "")
                    .replace("3.", "_3_")
                    .upper(),
                )
            except:
                raise RdkParametersInvalidError(
                    f"Invalid parameters found in Parameters.SourceRuntime. Current supported Lambda Runtime: {rdk_supported_custom_rule_runtime}"
                )

    def get_latest_rdklib_lambda_layer_version_arn(
        self, layer_name: str = "rdklib-layer"
    ):
        response = boto3.client("lambda").list_layer_versions(LayerName=layer_name)
        layer_versions = response["LayerVersions"]
        latest_version = sorted(layer_versions, key=lambda d: d["Version"])[-1]
        return latest_version["LayerVersionArn"]
