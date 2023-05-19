import sys

# from rdk.core.init import RdkInitializer
from rdk.utils.logger import get_main_logger


def run():
    """
    clean sub-command handler.
    """
    logger = get_main_logger()
    logger.info("AWS Config cleaning is starting ...")

    sys.exit(print("RDK clean"))
