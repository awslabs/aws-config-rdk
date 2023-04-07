"""
Well-known exceptions raised.
"""


class RdkParametersInvalidError(Exception):
    """
    Raise invalid parameters error when rdk failed to retrieve the parameters from parameters.json
    """
    def __init__(self, rule_dir):
        message = (
            f"Invalid parameters found in {rule_dir}"
        )

        super().__init__(message)

class RdkJsonInvalidError(Exception):
    """
    Raise invalid json error when rdk failed to decode parameters.json
    """
    def __init__(self, rule_dir):
        message = (
            f"Failed to decode JSON in parameters file in {rule_dir}"
        )

        super().__init__(message)

class RdkJsonLoadFailure(Exception):
    """
    Raise load failure exception when rdk failed to load parameters.json
    """
    def __init__(self, rule_dir):
        message = (
            f"Error loading parameters file in {rule_dir}"
        )

        super().__init__(message)

class RdkRuleTypesInvalidError(Exception):
    """
    Raise invalid source type error for non supporting types. 
    """

class RdkNotSupportedError(Exception):
    """
    Raise not supporting error for not supported action. 
    """

class RdkDuplicatedRuleNameError(Exception):
    """
    Raise invalid source type error for non supporting types. 
    """
    def __init__(self, rule_paths):
        message = (
            f"Found duplicated rule name in the following paths: {rule_paths}"
        )

        super().__init__(message)
