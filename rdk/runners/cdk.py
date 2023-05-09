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
class CdkRunner(BaseRunner):
    """
    Helper class to run cdk commands.
    https://docs.aws.amazon.com/cdk/v2/guide/hello_world.html.

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
        # TODO - should this actually be the CDK application's path? I don't understand what Ricky was doing here.
        self.cdk_app_dir = Path(__file__).resolve().parent.parent / "frameworks" / "cdk"

    def synthesize(self):
        """
        Executes `cdk synth`.

        Parameters:

        """
        cmd = [
            "cdk",
            "synth",
            "--validation",
            "--output",
            self.rules_dir.joinpath("build/").as_posix(),
            # "--version-reporting",
            # "false",
            # "--path-metadata",
            # "false",
            # "--asset-metadata",
            # "false",
            "--context",
            "rules_dir=" + self.rules_dir.as_posix(),
        ]

        self.logger.info("Synthesizing CloudFormation template(s)...")

        self.run_cmd(
            cmd=cmd,
            cwd=self.cdk_app_dir.as_posix(),
            allowed_return_codes=[0, 2],
        )

    def diff(self):
        """
        Executes `cdk diff`.

        Parameters:

        """
        cmd = [
            "cdk",
            "diff",
            "--context",
            "rules_dir=" + self.rules_dir.as_posix(),
        ]

        self.logger.info(
            f"Showing differences on CloudFormation template(s) for rule {self.rules_dir.as_posix()}..."
        )

        self.logger.info(
            f"Running cmd {cmd} in directory {self.cdk_app_dir.as_posix()}..."
        )

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
            "rules_dir=" + self.rules_dir.as_posix(),
        ]

        self.logger.info("Environment Bootstrapping ...")

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
            "--app",
            (self.cdk_app_dir / "cdk.out").as_posix(),
            "--context",
            "rules_dir=" + self.rules_dir.as_posix(),
            "--require-approval",
            "never",
        ]

        self.logger.info("Deploying AWS Config Rules ...")

        self.run_cmd(
            cmd=cmd,
            cwd=self.cdk_app_dir.as_posix(),
            allowed_return_codes=[0, 2],
        )

    def destroy(self):
        """
        Executes `cdk destroy`.

        Parameters:

        """
        cmd = [
            "cdk",
            "destroy",
            "--context",
            "rules_dir=" + self.rules_dir.as_posix(),
            "--force",
        ]

        self.logger.info("Destroying AWS Config Rules ...")

        self.run_cmd(
            cmd=cmd,
            cwd=self.cdk_app_dir.as_posix(),
            allowed_return_codes=[0, 2],
        )
