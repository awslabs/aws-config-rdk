#    Copyright 2017-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
#
#        http://aws.amazon.com/apache2.0/
#
#    or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

import concurrent.futures
import copy
import six

if six.PY2:
    import rdk
else:
    from rdk import rdk


def main():
    # Set up command-line argument parser and parse the args.
    my_parser = rdk.get_command_parser()
    args = my_parser.parse_args()
    my_rdk = rdk.rdk(args)

    if args.region_file:
        if args.command in ['init', 'deploy', 'undeploy']:
            regions = rdk.parse_region_file(args)

            args_list = []
            for region in regions:
                vars(args)['region'] = region
                args_list.append(copy.copy(args))

            data = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
                future_run_multi_region = {executor.submit(rdk.run_multi_region, args): args for args in args_list}
                for future in concurrent.futures.as_completed(future_run_multi_region):
                    data.append(future.result())
            exit(0)
        else:
            my_parser.error("Command must be 'init', 'deploy', or 'undeploy' when --region-file argument is provided.")

    return_val = my_rdk.process_command()
    exit(return_val)
