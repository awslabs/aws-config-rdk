from aws_cdk import Stack
from pathlib import Path
from .errors import RdkJsonInvalidError, RdkJsonLoadFailure, RdkDuplicatedRuleNameError, RdkParametersInvalidError, RdkNotSupportedError
import json

rdk_supported_custom_rule_runtime = [
        "python3.7",
        "python3.7-lib",
        "python3.8",
        "python3.8-lib",
        "python3.9",
        "python3.9-lib",
        "nodejs6.10",
        "nodejs8.10",
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

    return validate(parameters_json)

def get_rule_name(rule_path: Path):
    try:
        rule_name = get_rule_parameters(rule_path)["Parameters"]["RuleName"]
    except Exception as e:
        raise  RdkParametersInvalidError("Invalid parameters found in Parameters.RuleName")
    if len(rule_name) > 128:
        raise RdkParametersInvalidError("Error: Found Rule with name over 128 characters: {rule_name} \n Recreate the Rule with a shorter name.")

    return rule_name

def get_deploy_rules_list(rules_dir: Path, deployment_mode: str = "all",):
    deploy_rules_list = []
    print(rules_dir.absolute())
    for path in rules_dir.absolute().glob("**/parameters.json"):
        print(path)
        if rules_dir.absolute().joinpath("rdk").as_posix() not in path.as_posix():
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
    
    print(deploy_rules_list)
    return deploy_rules_list

def validate(parameters_json: dict):
    #TODO
    return parameters_json