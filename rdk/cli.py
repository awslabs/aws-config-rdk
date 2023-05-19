#    Copyright 2017-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
#
#        http://aws.amazon.com/apache2.0/
#
#    or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

import concurrent.futures
import copy

from rdk import rdk


def main():
    # Set up command-line argument parser and parse the args.
    my_parser = rdk.get_command_parser()
    args = my_parser.parse_args()
    my_rdk = rdk.rdk(args)

    if args.region_file:
        if args.command in ["init", "deploy", "undeploy", "deploy-organization", "undeploy-organization"]:
            regions = rdk.parse_region_file(args)
            print(f"{args.command.capitalize()}ing rules in the following regions: {regions}.")
            if args.command in ["undeploy", "undeploy-organization"] and "--force" not in args.command_args:
                my_input = input("Delete specified Rules and Lambda Functions from your AWS Account? (y/N): ")
                while my_input.lower() not in ["y", "n"]:
                    my_input = input(f"Invalid input: {my_input}. Please enter either 'y' or 'n': ")
                if my_input.lower() == "y":
                    vars(args)["command_args"].append("--force")
                elif my_input.lower() == "n" or my_input == "":
                    exit(0)

            args_list = []
            for region in regions:
                vars(args)["region"] = region
                args_list.append(copy.copy(args))

            data = []
            with concurrent.futures.ProcessPoolExecutor(max_workers=16) as executor:
                future_run_multi_region = {executor.submit(rdk.run_multi_region, args): args for args in args_list}
                for future in concurrent.futures.as_completed(future_run_multi_region):
                    data.append(future.result())
            exit(0)
        else:
            my_parser.error("Command must be 'init', 'deploy', or 'undeploy' when --region-file argument is provided.")

    return_val = my_rdk.process_command()
    exit(return_val)
