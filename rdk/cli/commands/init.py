import sys

# from rdk.core.init import RdkInitializer
from rdk.utils.logger import get_main_logger


def run():
    """
    init sub-command handler.
    """
    logger = get_main_logger()
    logger.info("AWS Config initializing is starting ...")

    sys.exit(print("RDK initializer"))
