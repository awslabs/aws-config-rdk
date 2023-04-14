import copy
import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import rdk as this_pkg
from rdk.runners.base import BaseRunner


@dataclass
class CfnGuardRunner(BaseRunner):
    """
    Helper class to run cfn-guard commands. https://docs.aws.amazon.com/cfn-
    guard/latest/ug/testing-rules.html.

    Parameters:

    * **`rules_file`** (_Path_): Provides the name of a rules file.
    * **`config`** (_Config_): Provides the name of a file or directory for data files in either JSON or YAML format.

    """

    rules_file: Path
    test_data: Path
    verbose: bool = False

    def __post_init__(self):
        super().__post_init__()

    def test(self):
        """
        Executes `cfn-guard test`.

        Parameters:

        """
        cmd = [
            "cfn-guard",
            "test",
            "--rules-file",
            self.rules_file.as_posix(),
            "--test-data", 
            self.test_data.as_posix()
        ]

        if self.verbose:
            cmd.append("--verbose")

        self.logger.info(f"Running cfn-guard unit test on {self.rules_file.relative_to(self.rules_file.parent.parent)} with testing data: {self.test_data.relative_to(self.rules_file.parent.parent)}")

        return self.run_cmd(
            cmd=cmd,
            cwd=Path().absolute().as_posix(),
            capture_output=True
        )

