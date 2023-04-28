import argparse
import logging
import os
from pathlib import Path

import rdk as this_pkg
import rdk.cli.commands.deploy as deploy_cmd
import rdk.cli.commands.init as init_cmd
import rdk.cli.commands.test as test_cmd
import rdk.cli.commands.destroy as destroy_cmd
import rdk.utils.logger as rdk_logger


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

    # init
    commands_parser.add_parser(
        "init",
        help="Sets up AWS Config.  This will enable configuration recording in AWS and ensure necessary S3 buckets and IAM Roles are created.",
    )

    # deploy
    commands_parser_deploy = commands_parser.add_parser(
        "deploy",
        help="deploy AWS Config Rules",
    )

    commands_parser_deploy.add_argument(
        "rulename",
        metavar="<rulename>",
        nargs="*",
        default="",
        help="Rule name(s) to deploy.  Rule(s) will be pushed to AWS.",
    )

    commands_parser_deploy.add_argument(
        "-n",
        "--dryrun",
        action="store_true",
        default=False,
        help="Dry run mode",
    )

    # test
    commands_parser_test = commands_parser.add_parser(
        "test",
        help="deploy AWS Config Rules",
    )

    commands_parser_test.add_argument(
        "rulename",
        metavar="<rulename>",
        nargs="*",
        default="",
        help="Rule name(s) to test. Unit test of the rule(s) will be executed.",
    )

    commands_parser_test.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Verbose mode",
    )

    # destroy
    commands_parser_destroy = commands_parser.add_parser(
        "destroy",
        help="destroy AWS Config Rules",
    )

    commands_parser_destroy.add_argument(
        "rulename",
        metavar="<rulename>",
        nargs="*",
        default="",
        help="Rule name(s) to destroy.  Rule(s) will be removed.",
    )

    commands_parser_destroy.add_argument(
        "-n",
        "--dryrun",
        action="store_true",
        default=False,
        help="Dry run mode",
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
        deploy_cmd.run(
            rulenames=args.rulename,
            dryrun=args.dryrun,
        )

    # handle: test
    if args.command == "test":
        test_cmd.run(
            rulenames=args.rulename,
            verbose=args.verbose,
        )

    # handle: destroy
    if args.command == "destroy":
        destroy_cmd.run(
            rulenames=args.rulename,
            dryrun=args.dryrun,
        )
