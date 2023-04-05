import copy
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import rdk as this_pkg
from rdk.runners.base import BaseRunner


@dataclass
class CdkRunner(BaseRunner):
    """
    Helper class to run cdk commands.
    https://docs.aws.amazon.com/cdk/v2/guide/hello_world.html

    Parameters:

    * **`root_module`** (_Path_): Path to the cdk root module
    * **`config`** (_Config_): `rdk.core.config.Config` object

    """

    root_module: Path
    rules_dir: Path

    def __post_init__(self):
        super().__post_init__()


    def synthesize(self):
        """
        Executes `cdk synth`.

        Parameters:
        """
        cmd = [
            "cdk",
            "synth"
        ]


        self.logger.info("Synthsizing CloudFormation template(s)...")
        self.logger.info(self.root_module.as_posix())
        self.logger.info(self.rules_dir)


        self.run_cmd(
            cmd=cmd,
            cwd=self.root_module.as_posix(),
            allowed_return_codes=[0, 2],
        )
