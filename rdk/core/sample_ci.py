import json
import os

TEMPLATE_DIR = "templates"
SAMPLE_CI_DIR = "ci_examples"

"""
SUMMARY
This class takes the name of a CloudFormation resource and loads an example JSON representing its CI.
"""


class TestCI:
    def __init__(self, ci_type):
        # convert ci_type string to filename format
        ci_file = ci_type.replace("::", "_") + ".json"
        try:
            self.ci_json = json.load(
                open(
                    os.path.join(
                        os.path.dirname(__file__), TEMPLATE_DIR, SAMPLE_CI_DIR, ci_file
                    ),
                    "r",
                )
            )
        except FileNotFoundError:
            resource_url = "https://github.com/awslabs/aws-config-resource-schema/blob/master/config/properties/resource-types/"
            print(
                "No sample CI found for "
                + ci_type
                + ", even though it appears to be a supported CI.  Please log an issue at https://github.com/awslabs/aws-config-rdk."
                + f"\nLook here: {resource_url} for additional info"
            )
            exit(1)  # TODO - Is this too aggressive?

    def get_json(self):
        return self.ci_json
