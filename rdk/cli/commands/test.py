import sys
from typing import Any, Callable, Dict, List, Optional

from rdk.core.rules_test import RulesTest
from rdk.utils.logger import get_main_logger


# TODO - should this be named test_local for consistency with RDK v0?
def run(rulenames: List[str], verbose=False):
    """
    test sub-command handler.
    """
    logger = get_main_logger()
    logger.info("RDK is starting ...")

    sys.exit(RulesTest(rulenames=rulenames, verbose=verbose).run())
