import sys
from pathlib import Path

from typing import Any, Callable, Dict, List, Optional

from rdk.core.rules_deploy import RulesDeploy
from rdk.utils.logger import get_main_logger


def run(rulenames: List[str], dryrun: bool, rules_dir: str):
    """
    Deploy sub-command handler.
    """
    logger = get_main_logger()
    logger.info("RDK is starting ...")

    sys.exit(
        RulesDeploy(rulenames=rulenames, dryrun=dryrun, rules_dir=Path(rules_dir)).run()
    )
