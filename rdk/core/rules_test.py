import json
import logging
import time
import unittest
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List

import rdk.utils.logger as rdk_logger
from rdk.frameworks.cdk.cdk.core.rule_parameters import (
    get_deploy_rules_list,
    get_rule_name,
    get_rule_parameters,
)
from rdk.runners.cfn_guard import CfnGuardRunner


@dataclass
class RulesTest:
    """
    Defines rules for unit test.

    Parameters:

    * **`rulenames`** (_str_): list of rule names to deploy

    """

    rulenames: List[str]
    verbose: bool = False

    logger: logging.Logger = field(init=False)

    def __post_init__(self):
        self.logger = rdk_logger.get_main_logger()

    def run(self):
        self.logger.info("Running local test!")
        tests_successful = True
        rules_list = []
        test_report = {
            "pytest_results": [],
            "cfn_guard_results": []
        }
        cwd = Path().absolute()

        # Construct our list of rules to test.
        if self.rulenames:
            rules_list = [cwd.joinpath(rulename) for rulename in self.rulenames]
        else:
            rules_list = get_deploy_rules_list(rules_dir=cwd)

        for rule_path in rules_list:
            rule_name = get_rule_name(rule_path)
            rule_parameters = get_rule_parameters(rule_path)
            runtime = rule_parameters["Parameters"]["SourceRuntime"]

            self.logger.info("Testing " + rule_name)
            test_dir = cwd.joinpath(rule_path)
            self.logger.info("Looking for tests in " + test_dir.as_posix())

            if runtime in (
                "python3.7",
                "python3.7-lib",
                "python3.8",
                "python3.8-lib",
                "python3.9",
                "python3.9-lib",
            ):
                test_report["pytest_results"].append(self._run_pytest(test_dir))
            elif runtime in ["cloudformation-guard2.0", "guard-2.x.x"]:
                test_report["cfn_guard_results"] += self._run_cfn_guard_test(test_dir)
            else:
                self.logger.info(f"Skipping {rule_name} - The Custom Rule Runtime provided or Managed Rule is not supported for unit testing.")

        exit(self._result_summary(test_report))

    def _run_pytest(self, test_dir: Path):
        loader = unittest.TestLoader()
        suite = loader.discover(test_dir, pattern = "*_test.py")
        results = unittest.TextTestRunner(buffer=self.verbose, verbosity=2).run(suite)
        if len(results.errors) == 0 and len(results.failures) == 0:
            status = "PASSED" 
        else:
            status = "FAILED"
        return { "rule_dir": test_dir.name, "status": status,"test_run": results.testsRun, "errors": results.errors, "failures": results.failures }

    def _run_cfn_guard_test(self, test_dir: Path):
        report = []
        results = ""
        for test_path in test_dir.glob("**/*"):
            self.logger.info(f"Running test {test_path}")
            self.logger.info(f"Test file: {test_path.suffix} {test_path.name}")
            if test_path.suffix in [".json", ".yaml", ".yml"] and test_path.name != "parameters.json":
                cfn_guard_runner = CfnGuardRunner(rules_file=test_dir.joinpath("rule_code.guard"), test_data=test_path, verbose=self.verbose)
                try:
                    results = cfn_guard_runner.test()
                    report.append({"rule_dir": f"{test_dir.name}/{test_path.name}", "status": "PASSED", "test_run": results.count("Test Case #"), "errors": [], "failures": []})
                except Exception as e:
                    report.append({"rule_dir": f"{test_dir.name}/{test_path.name}", "status": "FAILED", "test_run": results.count("Test Case #"), "errors": [e], "failures": [results]})
        return report
    
    def _result_summary(self, test_report: Dict[str, Any]):
        pytest_results = test_report["pytest_results"]
        cfn_guard_results = test_report["cfn_guard_results"]

        self.logger.info("")
        self.logger.info("Test Summary:")
        self.logger.info("===============")
        self.logger.info("Pytest Results")
        self.logger.info("===============")
        exit_code = self._show_result(pytest_results)
        self.logger.info("================")
        self.logger.info("CfnGuard Results")
        self.logger.info("================")
        exit_code = self._show_result(cfn_guard_results) and exit_code
        return exit_code

    def _show_result(self, report_results: Dict[str, Any]):    
        exit_code = 0
        for result in report_results:
            self.logger.info(f"{result['rule_dir']} - ")
            self.logger.info(f"\tStatus: {result['status']} tests_run:{result['test_run']}")
            if result["errors"]:
                exit_code = 1
                for error in result["errors"]:
                    self.logger.info(f"\tError found: {error}")
            if result["failures"]:
                exit_code = 2
                for failure in result["failures"]:
                    if failure != "":
                        self.logger.info(f"\tTest failures found: {failure}") 
        return exit_code
