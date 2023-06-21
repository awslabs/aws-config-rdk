#!/usr/bin/env python
import os
from pathlib import Path

import aws_cdk as cdk
from cdk.cdk_stack import CdkStack
from aws_cdk import DefaultStackSynthesizer

"""
NOTES

This CDK app is expected to be executed from the `frameworks\cdk` folder.

This module supports two execution modes.
1. ALL
Deploys all the rules in the rules directory
A CFT stack will be created/updated for each rule in the directory

2. Specific Rules
Deploys the specified rules that were passed to the RDK CLI
A CFT stack will be created/updated for each specified rule
"""
app = cdk.App()
rules_dir = Path(app.node.try_get_context("rules_dir"))
rulename_str: str = app.node.try_get_context("rulename")
rule_names = rulename_str.split("|")  # Assumes a pipe-delimited list of rulenames
if not rule_names:
    raise Exception("Need either --all or specific rule name(s).")

for rule_name in rule_names:
    CdkStack(
        scope=app,
        construct_id=rule_name.replace("_", ""),
        rule_name=rule_name,
        rules_dir=rules_dir,
        # Suppresses Bootstrap-related conditions and metadata
        synthesizer=DefaultStackSynthesizer(generate_bootstrap_version_rule=False),
    )

app.synth()
