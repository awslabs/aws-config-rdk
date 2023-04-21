import json
from pathlib import Path

from aws_cdk import Stack

from .errors import (
    RdkDuplicatedRuleNameError,
    RdkJsonInvalidError,
    RdkJsonLoadFailure,
    RdkNotSupportedError,
    RdkParametersInvalidError,
)

rdk_supported_custom_rule_runtime = [
        "python3.7",
        "python3.7-lib",
        "python3.8",
        "python3.8-lib",
        "python3.9",
        "python3.9-lib",
        "python3.10",
        "python3.10-lib",
        # "nodejs6.10",
        # "nodejs8.10",
    ]

def get_rule_parameters(rule_dir: Path):
    parameters_txt = rule_dir.joinpath("parameters.json").read_text()
    parameters_json = {}

    try:
        parameters_json = json.loads(parameters_txt)
    except ValueError as ve:
        raise RdkJsonInvalidError(rule_dir)
    except Exception as e:
        raise RdkJsonLoadFailure(rule_dir)

    return validate(rule_dir, parameters_json)

def get_rule_name(rule_path: Path):
    rule_parameters = get_rule_parameters(rule_path)
    try:
        rule_name = rule_parameters["Parameters"]["RuleName"]
    except Exception as e:
        raise  RdkParametersInvalidError(f"Invalid parameters found in Parameters.RuleName in {rule_path}")
    if len(rule_name) > 128:
        raise RdkParametersInvalidError("Error: Found Rule with name over 128 characters: {rule_name} \n Recreate the Rule with a shorter name.")

    return rule_name

def get_deploy_rules_list(rules_dir: Path, deployment_mode: str = "all",):
    deploy_rules_list = []
    for path in rules_dir.absolute().glob("**/parameters.json"):
        if "build/" not in path.as_posix():
            if deployment_mode == "all":
                deploy_rules_list.append(path.parent)
                    # Add support for java and cs 
            # elif deployment_mode == "rule_names":
            #     for path in rules_dir.absolute().glob("**/parameters.json"):
            #         if rules_dir.absolute().joinpath("rdk").as_posix() not in path.as_posix():
            #             if command_arg == get_rule_name(path.parent):
            #                 rule_dir_paths.append(path.parent.as_posix())
            #     if len(rule_dir_paths) > 1: 
            #         raise RdkDuplicatedRuleNameError(rule_dir_paths)
            else:
                raise RdkNotSupportedError('Invalid Option: Specify Rule Name or RuleSet or empty for all.')
    
    return deploy_rules_list

def validate(rule_dir: Path, parameters_json: dict):
    #TODO
    latest_schema_version = "1.0"
    if "Parameters" not in parameters_json:
        raise RdkParametersInvalidError(f"Error in {rule_dir}: Missing Parameters Key")
    if "Version" not in parameters_json and parameters_json["Version"] != latest_schema_version:
        raise RdkParametersInvalidError(f"Error in {rule_dir}: Missing Version Key. The latest supported schema version is {latest_schema_version}")
    if "SourceIdentifier" not in parameters_json["Parameters"] and "SourceRuntime" not in parameters_json["Parameters"]:
        raise RdkParametersInvalidError(f"Error in {rule_dir}: Missing Parameters.SourceIdentifier or Parameters.SourceRuntime is required")
    if "SourcePeriodic" not in parameters_json["Parameters"] and "SourceEvents" not in parameters_json["Parameters"]:
        raise RdkParametersInvalidError(f"Error in {rule_dir}: Missing Parameters.SourcePeriodic or Parameters.SourceEvents is required")
    return parameters_json