import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import rdk.utils.logger as rdk_logger
from rdk.runners.cdk import CdkRunner


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
        Runs Rules Deployment.
        """
        if len(self.rulenames) > 0:
            rules_dir = Path(self.rulenames[0])
        else:
            rules_dir=Path().absolute() 

        cdk_runner = CdkRunner(
            rules_dir=rules_dir
        )

        cdk_runner.synthesize()
        cdk_runner.bootstrap()
        cdk_runner.deploy()

    def destroy(self):
        """
        Destroy Rules Deployment.
        """
        if len(self.rulenames) > 0:
            rules_dir = Path(self.rulenames[0])
        else:
            rules_dir=Path().absolute() 

        cdk_runner = CdkRunner(
            rules_dir=rules_dir
        )
        cdk_runner.destroy()
