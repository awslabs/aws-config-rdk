import argparse
import logging
import os
from pathlib import Path

import rdk as this_pkg
import rdk.cli.commands.deploy as deploy_cmd
import rdk.cli.commands.init as init_cmd
import rdk.cli.commands.test as test_cmd
import rdk.cli.commands.undeploy as destroy_cmd
import rdk.cli.commands.sample_ci as sample_ci_cmd
import rdk.utils.logger as rdk_logger
from rdk.core.get_accepted_resource_types import get_accepted_resource_types


def main():
    """
    Main CLI handler.
    """
    # Main parser
    main_parser = argparse.ArgumentParser(
        prog=this_pkg.CLI_NAME,
        description=this_pkg.DESCRIPTION,
        allow_abbrev=False,
    )
    main_parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=this_pkg.VERSION,
        help="show the version and exit",
    )

    # --quiet and --debug are mutually exclusive
    log_options = main_parser.add_mutually_exclusive_group()
    log_options.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        default=False,
        help="suppress informational logs",
    )
    log_options.add_argument(
        "-d",
        "--debug",
        action="store_true",
        default=False,
        help="display debug logs",
    )

    # Commands parser
    commands_parser = main_parser.add_subparsers(
        title="commands",
        dest="command",
        required=True,
        metavar="<command>",
        help=f"Use {this_pkg.NAME} <command> --help for detailed usage",
    )

    # Reusable arguments
    rulename_arg = {
        "dest": "rulename",
        "metavar": "<rulename>",
        "nargs": "*",
        "default": "",
        "help": "Rule name(s) to perform this command on.",
    }
    dryrun_name_or_flags = [
        "-n",
        "--dryrun",
    ]
    dryrun_arg = {
        "dest": "dryrun",
        "action": "store_true",
        "default": False,
        "help": "Dry run mode",
    }

    all_arg = {
        "dest": "all",
        "action": "store_true",
        "default": False,
        "help": "If specified, runs the RDK command for all rules in the directory.",
    }

    rule_dir_arg = {
        "dest": "rules_dir",
        "default": os.getcwd(),
        "help": "This arg is mainly used for testing -- it allows you to specify a different rule directory than the CWD as the holder of RDK rule folders",
    }

    # COMMAND-SPECIFIC PARSERS

    # INIT
    commands_parser.add_parser(
        "init",
        help="Sets up AWS Config.  This will enable configuration recording in AWS and ensure necessary S3 buckets and IAM Roles are created.",
    )

    # DEPLOY
    commands_parser_deploy = commands_parser.add_parser(
        "deploy",
        help="deploy AWS Config Rules",
    )

    # Can either specify rule names or --all
    rule_args_parser_deploy = commands_parser_deploy.add_mutually_exclusive_group()
    rule_args_parser_deploy.add_argument(**rulename_arg)
    rule_args_parser_deploy.add_argument("--all", **all_arg)

    commands_parser_deploy.add_argument("--rules-dir", **rule_dir_arg)
    commands_parser_deploy.add_argument(*dryrun_name_or_flags, **dryrun_arg)

    # TEST
    commands_parser_test = commands_parser.add_parser(
        "test",
        help="deploy AWS Config Rules",
    )

    commands_parser_test.add_argument(**rulename_arg)

    commands_parser_test.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Verbose mode",
    )

    # UNDEPLOY
    commands_parser_destroy = commands_parser.add_parser(
        "undeploy",
        help="destroy AWS Config Rules",
    )

    rule_args_parser_destroy = commands_parser_destroy.add_mutually_exclusive_group()
    rule_args_parser_destroy.add_argument(**rulename_arg)
    rule_args_parser_destroy.add_argument("--all", **all_arg)

    commands_parser_destroy.add_argument("--rules-dir", **rule_dir_arg)
    commands_parser_destroy.add_argument(*dryrun_name_or_flags, **dryrun_arg)

    # SAMPLE-CI
    commands_parser_sample_ci = commands_parser.add_parser(
        "sample-ci",
        help="Provides a way to see sample configuration items for most supported resource types.",
    )

    commands_parser_sample_ci.add_argument(
        "ci_type",
        metavar="<resource type>",
        help='Resource name (e.g. "AWS::EC2::Instance") to display a sample CI JSON document for.',
        choices=get_accepted_resource_types(),
    )

    # _pytest -- hidden command used by pytests
    commands_parser.add_parser(
        "_pytest",
    )

    # Parse all args and commands
    args = main_parser.parse_args()

    # Init logger
    logger = rdk_logger.init_main_logger()

    # Adjust log levels
    if args.quiet:
        rdk_logger.update_stream_handler_level(logger=logger, level=logging.WARNING)
    if args.debug:
        rdk_logger.update_stream_handler_level(logger=logger, level=logging.DEBUG)

    # handle: _pytest (do nothing)
    if args.command == "_pytest":
        pass

    # handle: init
    if args.command == "init":
        init_cmd.run()

    # handle: deploy
    if args.command == "deploy":
        # Any subdirectory of rules_dir with a parameters.json file in it is assumed to be a Rule
        if args.all:
            rulenames = [
                f.name
                for f in os.scandir(args.rules_dir)
                if f.is_dir() and os.path.exists(os.path.join(f, "parameters.json"))
            ]
        else:
            rulenames = args.rulename
        deploy_cmd.run(
            rulenames=rulenames, dryrun=args.dryrun, rules_dir=args.rules_dir
        )

    # handle: test
    if args.command == "test":
        test_cmd.run(
            rulenames=args.rulename,
            verbose=args.verbose,
        )

    # handle: undeploy
    if args.command == "undeploy":
        if args.all:
            rulenames = [f.name for f in os.scandir(args.rules_dir) if f.is_dir()]
        else:
            rulenames = args.rulename
        destroy_cmd.run(
            rulenames=args.rulename, dryrun=args.dryrun, rules_dir=args.rules_dir
        )

    # handle: sample-ci
    if args.command == "sample-ci":
        sample_ci_cmd.run(
            resource_type=args.ci_type,
        )
