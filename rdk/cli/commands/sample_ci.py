import argparse
import json
import sys

# from rdk.core.init import RdkInitializer
from rdk.utils.logger import get_main_logger
from rdk.core.get_accepted_resource_types import get_accepted_resource_types
from rdk.core.sample_ci import TestCI


def run(resource_type: str):
    """
    sample-ci sub-command handler.
    """
    logger = get_main_logger()
    logger.info("AWS Config sample CI is starting ...")
    my_test_ci = TestCI(resource_type)
    print(json.dumps(my_test_ci.get_json(), indent=4))
    print(
        f"For more info, try checking: https://github.com/awslabs/aws-config-resource-schema/blob/master/config/properties/resource-types/"
    )
    sys.exit(0)  # TODO - Necessary?
