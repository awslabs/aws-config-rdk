import sys

# from rdk.core.init import RdkInitializer
from rdk.utils.logger import get_main_logger


def run():
    """
    create rule template sub-command handler.
    """
    logger = get_main_logger()
    logger.info("AWS Config create rule template is starting ...")

    sys.exit(print("RDK creating rule template"))
