import sys
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path
from rdk.core.rules_deploy import RulesDeploy
from rdk.utils.logger import get_main_logger


def run(rulenames: List[str], dryrun: bool, rules_dir: str):
    """
    test sub-command handler.
    """
    logger = get_main_logger()
    logger.info("Destroying RDK rules ...")

    sys.exit(
        RulesDeploy(
            rulenames=rulenames, dryrun=dryrun, rules_dir=Path(rules_dir)
        ).destroy()
    )
