import copy
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional

import rdk as this_pkg
from rdk.runners.base import BaseRunner


@dataclass
class CdkRunner(BaseRunner):
    """
    Helper class to run cdk commands.
    https://docs.aws.amazon.com/cdk/v2/guide/hello_world.html

    Parameters:

    * **`rules_dir`** (_Path_): Path to the rules directory for deployment
    * **`cdk_app_dir`** (_Path_): Path to the embedded CDK framework root directory

    """

    rules_dir: Path
    cdk_app_dir: Path = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        # cdk_source_dir = Path(__file__).resolve().parent.parent /'frameworks' / 'cdk'
        # self.logger.info("Getting latest deployment framework from " + cdk_source_dir.as_posix())
        # self.logger.info("Deploying latest deployment framework in " + self.root_module.as_posix())
        # shutil.rmtree(self.root_module / "cdk")
        # shutil.copytree(Path(__file__).resolve().parent.parent /'frameworks' / 'cdk', self.root_module / 'cdk')
        # self.cdk_app_dir = self.root_module / "cdk"
        self.cdk_app_dir = Path(__file__).resolve().parent.parent /'frameworks' / 'cdk'

    def synthesize(self):
        """
        Executes `cdk synth`.

        Parameters:
        """
        cmd = [
            "cdk",
            "synth",
            "--context",
            "rules_dir=" + self.rules_dir.as_posix()
        ]


        self.logger.info("Synthesizing CloudFormation template(s)...")

        self.run_cmd(
            cmd=cmd,
            cwd=self.cdk_app_dir.as_posix(),
            allowed_return_codes=[0, 2],
        )

    def bootstrap(self):
        """
        Executes `cdk bootstrap`.

        Parameters:
        """
        cmd = [
            "cdk",
            "bootstrap",
            "--context",
            "rules_dir=" + self.rules_dir.as_posix()
        ]


        self.logger.info("Envrionment Bootstrapping ...")

        self.run_cmd(
            cmd=cmd,
            cwd=self.cdk_app_dir.as_posix(),
            allowed_return_codes=[0, 2],
        )

    def deploy(self):
        """
        Executes `cdk deploy`.

        Parameters:
        """
        cmd = [
            "cdk",
            "deploy",
            "--context",
            "rules_dir=" + self.rules_dir.as_posix(),
            "--require-approval",
            "never"
        ]


        self.logger.info("Deploying AWS Config Rules ...")

        self.run_cmd(
            cmd=cmd,
            cwd=self.cdk_app_dir.as_posix(),
            allowed_return_codes=[0, 2],
        )