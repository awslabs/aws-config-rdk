"""
Well-known exceptions raised by Rdk.
"""


class RdkError(Exception):
    """
    Base class for all Rdk errors.
    """


class RdkCommandInvokeError(RdkError):
    """
    Error occured when invoking a command.
    """


class RdkCommandExecutionError(RdkError):
    """
    Error occured when executing a command.
    """


class RdkCommandNotAllowedError(RdkError):
    """
    An unsupported command was requested to be executed.
    """
