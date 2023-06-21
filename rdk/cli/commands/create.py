import sys

# from rdk.core.init import RdkInitializer
from rdk.utils.logger import get_main_logger


def run():
    """
    create sub-command handler.
    """
    logger = get_main_logger()
    logger.info("AWS Config create is starting ...")

    sys.exit(print("NOT IMPLEMENTED YET - RDK would create a new rule folder"))
