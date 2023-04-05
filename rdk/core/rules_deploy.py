import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import rdk.utils.logger as rdk_logger
from rdk.runners.cdk import CdkRunner

def _resolve_path(
    root: Path,
    thing: Union[str, Path],
) -> Path:
    """
    Helper to resolve and verify paths.
    """
    resolved = (root / thing).resolve().absolute()
    if not resolved.exists():
        raise FileNotFoundError(resolved.as_posix())
    return resolved

@dataclass
class RulesDeploy:
    """
    Defines rules for deployment.

    Parameters:

    * **`rulenames`** (_str_): list of rule names to deploy

    """

    rulenames: List[str]
    dryrun: bool

    logger: logging.Logger = field(init=False)

    def __post_init__(self):
        self.logger = rdk_logger.get_main_logger()

    def run(self):
        """
        Runs Rules Deployment
        """

        rules_dir = Path(self.rulenames[0])

        cdk_runner = CdkRunner(
            root_module=Path("./cdk"),
            rules_dir=rules_dir
        )

        cdk_runner.synthesize()