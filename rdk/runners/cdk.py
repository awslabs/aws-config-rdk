import boto3
import copy
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from botocore.exceptions import ClientError

import rdk as this_pkg
from rdk.runners.base import BaseRunner
from rdk.core.errors import (
    RdkCommandExecutionError,
    RdkCommandInvokeError,
    RdkCommandNotAllowedError,
)


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
    rulenames: List[str]

    def __post_init__(self):
        super().__post_init__()
        # The CDK app is a standard app that takes rule definitions as context
        self.cdk_app_dir = Path(__file__).resolve().parent.parent / "frameworks" / "cdk"

    def get_context_args(
        self,
        # Rule names generally aren't included for CDK Diff
        include_rulenames=True,
        # To override the list of rulenames, eg. for only deploying a subset that need changes
        rulenames_override=[],
    ):
        context_args = [
            "--version-reporting",  # Setting this to false will exclude CDK Metadata
            "false",
            "--context",
            "rules_dir=" + self.rules_dir.as_posix(),
            "--context",
        ]

        if include_rulenames:
            if rulenames_override:
                deploy_rulenames = rulenames_override
            else:
                deploy_rulenames = self.rulenames
            context_args.append(
                f"\"rulename={'|'.join(deploy_rulenames)}\"",
            )
        return context_args

    def synthesize(self):
        """
        Executes `cdk synth`.

        Parameters:

        """
        cmd = [
            "cdk",
            "synth",
            "--quiet",  # TODO - does it make sense to not write to cdk.out?
            "--validation",
            # "--output",
            # self.rules_dir.joinpath("build/").as_posix(),
        ]
        cmd += self.get_context_args()

        self.logger.info("Synthesizing CloudFormation template(s)...")

        self.logger.debug(f"Running cmd {cmd} in directory {self.cdk_app_dir.as_posix()}...")

        self.run_cmd(
            cmd=cmd,
            cwd=self.cdk_app_dir.as_posix(),
            allowed_return_codes=[0, 2],
        )

    def get_deployed_stacks(self):
        """
        This is used to determine which stacks need to be CDK Diff'd vs which are fresh deploys
        """
        rule_names = self.rulenames
        existing_stack_rule_names = {}
        missing_stack_rule_names = {}
        for rule_name in rule_names:
            try:
                existing_stack_rule_names[rule_name] = (
                    boto3.client("cloudformation")
                    .describe_stacks(StackName=rule_name.replace("_", ""))
                    .get("Stacks", [])[0]
                    .get("StackName")
                )
            except ClientError as ex:
                self.logger.error(repr(ex))
                # Continue if stack is not found
                if re.search("(ValidationError)", repr(ex)):
                    self.logger.info(f"Stack {rule_name.replace('_', '')} not found, adding to missing stack list")
                    missing_stack_rule_names[rule_name] = rule_name.replace("_", "")
                    continue
                raise RdkCommandExecutionError("Unable to determine if stack exists.")
        return existing_stack_rule_names, missing_stack_rule_names

    def diff(self):
        """
        Executes `cdk diff`.

        The intention of this execution is to determine whether a full run of RDK deploy is required.

        If a stack has no differences compared to the deployed stack, it should be skipped. Otherwise, it should be redeployed.

        Parameters:
        None
        """
        stacks_with_diffs = []  # Keep a list of which stacks need to be updated
        deployed_stacks, missing_stacks = self.get_deployed_stacks()
        if not deployed_stacks and not missing_stacks:
            self.logger.info("No stacks requiring updates found for the given inputs.")
            return
        # Always deploy stacks if there is no existing Stack
        for missing_stack in missing_stacks.keys():
            stacks_with_diffs.append(missing_stack)
        # Review each deployed stack and compare it to the current template
        for deployed_stack in deployed_stacks.keys():
            cmd = [
                "cdk",
                "diff",
                "--fail",
                deployed_stacks[
                    deployed_stack
                ],  # Use the map of rule name to stack name, since they're used in different but related contexts
            ]
            context = self.get_context_args(include_rulenames=False)
            context.append(f"rulename={deployed_stack}")
            cmd += context

            self.logger.info(f"Showing differences on CloudFormation template(s) {deployed_stack}...")

            self.logger.debug(f"Running cmd {cmd} in directory {self.cdk_app_dir.as_posix()}...")

            return_code = self.run_cmd(
                cmd=cmd,
                cwd=self.cdk_app_dir.as_posix(),
                allowed_return_codes=[0, 1, 2],
            )
            if return_code == 1:
                stacks_with_diffs.append(deployed_stack)
        # Send a list of stack names to the caller
        return stacks_with_diffs

    def bootstrap(self):
        """
        Executes `cdk bootstrap`.

        Parameters:

        """
        cmd = [
            "cdk",
            "bootstrap",
        ]
        cmd += self.get_context_args()

        self.logger.info("Environment Bootstrapping ...")

        self.run_cmd(
            cmd=cmd,
            cwd=self.cdk_app_dir.as_posix(),
            allowed_return_codes=[0, 2],
        )

    def deploy(self, stacks_to_deploy):
        """
        Executes `cdk deploy`.

        Parameters:
        stacks_to_deploy: A list of stack names to deploy.
        """
        cmd = [
            "cdk",
            "deploy",
            " ".join(stacks_to_deploy).replace("_", ""),
            "--app",
            (self.cdk_app_dir / "cdk.out").as_posix(),
            "--require-approval",
            "never",
        ]
        cmd += self.get_context_args(
            rulenames_override=stacks_to_deploy,
        )

        self.logger.info("Deploying AWS Config Rules ...")

        self.logger.debug(f"Running cmd {cmd} in directory {self.cdk_app_dir.as_posix()}...")

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
            "--force",
        ]
        cmd += self.get_context_args()

        self.logger.info("Destroying AWS Config Rules ...")

        self.logger.debug(f"Running cmd {cmd} in directory {self.cdk_app_dir.as_posix()}...")

        self.run_cmd(
            cmd=cmd,
            cwd=self.cdk_app_dir.as_posix(),
            allowed_return_codes=[0, 2],
        )
