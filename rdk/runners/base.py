#
# NOTE:
# This class uses subprocess.run(...) which is, in some cases, subject
# to shell-injection attacks. However, in this case, we are
# (1) Using shell=False, to not use a shell (safer) and
# (2) Using a well known command in args
# For the most part, we should be using subprocess as safely as possible.
# The places that bandit warns about will be silenced with '# nosec'
#

import logging
import re
import selectors
import subprocess  # nosec
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TextIO

from rdk.core.errors import (
    RdkCommandExecutionError,
    RdkCommandInvokeError,
    RdkCommandNotAllowedError,
)

# from rdk.utils.logger import get_testcase_logger
from rdk.utils.logger import get_main_logger


@dataclass
class BaseRunner:
    """
    Base class for various command runners.
    """

    logger: logging.Logger = field(init=False)

    def __post_init__(self):
        # self.logger = get_testcase_logger()
        self.logger = get_main_logger()

    # Linter notes:
    # * Yes pylint, we know this method is complicated.
    # * bandit does not like subprocess. See note at the top of this file
    def run_cmd(  # pylint: disable=too-many-arguments,too-many-locals,too-many-statements
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        allowed_return_codes: Optional[List[int]] = None,
        capture_output: bool = False,
        discard_output: bool = False,
    ) -> str:
        """
        Runs a command using `subprocess.popen`.

        Parameters:

        * **`cmd`** (_list of str_): The command to run.
        * **`cwd`** (_str_): Optional directory to run the command in.
        * **`env`** (_mapping_): Optional mapping of environment variables to set.
        * **`allowed_return_codes`** (_list of int_): Optional list of acceptable return codes.
        * **`capture_output`** (_bool_): Optionally return stdout. Default is `False`
        * **`discard_output`** (_bool_): Optionally send stdout to dev-null. Default is `False`

        """

        if not allowed_return_codes:
            allowed_return_codes = [0]

        self._check_if_command_is_allowed(cmd[0])
        self.logger.debug(f"Running Command: {' '.join(cmd)}")

        subprocess_popen_kwargs = {
            "args": cmd,
            # RDK is always non-interactive
            "stdin": subprocess.DEVNULL,
            # output streams are logged by default
            # These will get changed below based on other flags
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            # We're only dealing with text streams for now
            "universal_newlines": True,
        }
        if cwd:
            subprocess_popen_kwargs["cwd"] = cwd
        if env:
            subprocess_popen_kwargs["env"] = env

        # Command output log handling flags
        # By default, we log stderr as INFO,
        # but relog it as ERROR upon a failure
        loglevel_stdout = logging.INFO
        loglevel_stderr = logging.INFO

        # What are we doing with outputs?
        if capture_output or discard_output:
            loglevel_stdout = logging.DEBUG
            loglevel_stderr = logging.ERROR

        # Linter ignores:
        # * mypy is not happy about `subprocess_run_kwargs`, it thinks we are
        #   passing a Dict[str, Obj]
        # * pylint does not recognize the `**` unpacking for kwargs
        # * bandit warns about `subprocess.run` in general. See note at the top
        #   of this file.

        # Default returns
        return_code = 255
        captured_stdout_lines = []
        captured_stderr_lines = []

        # Run
        try:
            with subprocess.Popen(**subprocess_popen_kwargs) as process:  # type: ignore[call-overload] # nosec
                # Read stdout and stderr streams
                selctr = selectors.DefaultSelector()
                for _maybe_fileobj in [process.stdout, process.stderr]:
                    if _maybe_fileobj is not None:
                        selctr.register(
                            fileobj=_maybe_fileobj, events=selectors.EVENT_READ
                        )

                def _log_streams(is_final: bool = False):
                    """
                    Log stuff based on stdout or stderr.
                    """
                    for _selkey, _ in selctr.select():
                        # NOTE: Selector key can be empty
                        if _selkey:
                            this_fileobj: TextIO = _selkey.fileobj  # type: ignore
                            for _line in iter(this_fileobj.readline, ""):
                                # Fixup lines
                                _line_no_escapes = re.sub(
                                    # Remove all escape sequences
                                    # https://superuser.com/a/380778
                                    r"\x1b\[[0-9;]*[a-zA-Z]",
                                    "",
                                    _line,
                                )
                                _line_rstripped = _line_no_escapes.rstrip()
                                _line_stripped = _line_no_escapes.strip()

                                # Decide what to do with them ...
                                if this_fileobj is process.stdout:
                                    # This line is a stdout
                                    if capture_output and _line_stripped:
                                        captured_stdout_lines.append(_line_stripped)
                                    if _line_rstripped:
                                        self.logger.log(
                                            level=loglevel_stdout,
                                            msg=_line_rstripped,
                                        )
                                if this_fileobj is process.stderr:
                                    # This line is a stderr
                                    if _line_stripped:
                                        captured_stderr_lines.append(_line_stripped)
                                    if _line_rstripped:
                                        self.logger.log(
                                            level=loglevel_stderr,
                                            msg=_line_rstripped,
                                        )

                                # If this is not the final call, iterate
                                # over each selector alternatively
                                if not is_final:
                                    break

                # Process streams while the command is running
                while process.poll() is None:
                    _log_streams()

                # Again, if stuff is leftover in the fd's
                time.sleep(0.10)
                _log_streams(is_final=True)

                # Get return code
                return_code = process.returncode
        except Exception as exc:
            self.logger.exception(exc)
            raise RdkCommandInvokeError("Failed to invoke requested command") from exc

        if return_code not in allowed_return_codes:
            # log any errors
            for _line in captured_stderr_lines:
                self.logger.error(_line)
            raise RdkCommandExecutionError(
                f"Command execution failed with an unacceptable exit code: {return_code}"
            )

        if capture_output:
            return "\n".join(captured_stdout_lines)

        return "OK"

    def get_python_executable(self) -> str:  # pylint: disable=no-self-use
        """
        Returns the current python executable.
        """
        current_python_executable = "python"
        if sys.executable:
            current_python_executable = sys.executable
        return current_python_executable

    def _check_if_command_is_allowed(self, cmd: str):
        if cmd not in [
            "cdk",
            "cfn-guard",
            self.get_python_executable(),
        ]:
            raise RdkCommandNotAllowedError(f"Unsupported command provided: {cmd}")
