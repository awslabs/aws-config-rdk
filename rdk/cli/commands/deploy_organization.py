import sys

# from rdk.core.init import RdkInitializer
from rdk.utils.logger import get_main_logger


def run():
    """
    deploy-organization sub-command handler.
    """
    logger = get_main_logger()
    logger.info("AWS Config deploy organization is starting ...")

    sys.exit(print("RDK deploying to organization"))
