import sys
from typing import Any, Callable, Dict, List, Optional

from rdk.core.rules_deploy import RulesDeploy
from rdk.utils.logger import get_main_logger


# TODO - should this be named undeploy for consistency with RDK v0?
def run(rulenames: List[str], dryrun: bool):
    """
    test sub-command handler.
    """
    logger = get_main_logger()
    logger.info("Destroying RDK rules ...")

    sys.exit(RulesDeploy(rulenames=rulenames, dryrun=dryrun).destroy())
