import logging
import sys
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
    rules_dir: Path

    logger: logging.Logger = field(init=False)

    def __post_init__(self):
        self.logger = rdk_logger.get_main_logger()

    def runner_setup(self):
        """
        Validate rule arguments and create a CDK Runner
        """
        if not self.rules_dir:
            self.logger.error(
                "Invalid option, must specify a rule name, rule set, or explicitly use '--all'."
            )
            sys.exit(0)
        # This logic ensures that the rule name will be used for stack names/rule names instead of the full path
        rule_names_no_path = []
        for rulepath in self.rulenames:
            rule_names_no_path.append(Path(rulepath).name)
        self.cdk_runner = CdkRunner(
            rules_dir=self.rules_dir,
            rulenames=rule_names_no_path,
        )

    def run(self):
        """
        Runs Rules Deployment.
        """
        self.runner_setup()

        stacks_to_deploy = self.cdk_runner.diff()
        if not stacks_to_deploy:
            self.logger.info("No changes to deploy.")
            return
        # self.cdk_runner.synthesize() # cdk diff will perform a synth behind the scenes, making this synth unnecessary
        self.cdk_runner.bootstrap()  # TODO - parameter to skip bootstrap? Could speed things up a bit
        self.cdk_runner.deploy(stacks_to_deploy)

    def destroy(self):
        """
        Destroy Rules Deployment.
        """
        self.runner_setup()
        self.cdk_runner.destroy()
