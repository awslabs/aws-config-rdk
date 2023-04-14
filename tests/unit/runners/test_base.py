import logging
import subprocess
import sys
import uuid

import pytest
from pytest_mock import MockerFixture

from rdk.core.errors import (
    RdkCommandExecutionError,
    RdkCommandInvokeError,
    RdkCommandNotAllowedError,
)
from rdk.runners.base import BaseRunner


def test__check_if_command_is_allowed():
    runner = BaseRunner()
    for cmd in [
        "cdk",
    ]:
        runner._check_if_command_is_allowed(cmd)

    with pytest.raises(RdkCommandNotAllowedError):
        runner._check_if_command_is_allowed("foo")


def test_get_python_executable(monkeypatch: pytest.MonkeyPatch):
    runner = BaseRunner()
    with monkeypatch.context() as m:
        m.setattr(sys, "executable", None)
        assert runner.get_python_executable() == "python"


def test_run_cmd_basic(mocker: MockerFixture):
    # Init
    runner = BaseRunner()
    subprocess_popen_mock = mocker.patch("subprocess.Popen")
    subprocess_popen_mock.return_value.__enter__().returncode = 0
    mocker.patch("selectors.DefaultSelector")

    # Test basic arguments pass-thru
    runner.run_cmd(
        cmd=["cdk", "--version"],
        cwd="test",
        env={
            "test": "test",
        },
    )
    subprocess_popen_mock.assert_called_with(
        args=["cdk", "--version"],,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        cwd="test",
        env={
            "test": "test",
        },
    )

    # Test bad commands
    subprocess_popen_mock.reset_mock(return_value=True, side_effect=True)
    subprocess_popen_mock.side_effect = FileNotFoundError("File foo does not exist")
    with pytest.raises(RdkCommandInvokeError):
        runner.run_cmd(cmd=["cdk", "--version"],)

    # Test return codes
    subprocess_popen_mock.reset_mock(return_value=True, side_effect=True)
    subprocess_popen_mock.return_value.__enter__().returncode = 2
    with pytest.raises(RdkCommandExecutionError):
        runner.run_cmd(cmd=["cdk", "--version"],, allowed_return_codes=[1])


def test_run_cmd_logging(
    caplog: pytest.LogCaptureFixture,
):
    this_python = sys.executable

    caplog.set_level(logging.DEBUG)
    runner = BaseRunner()

    # Basic logs
    runner.run_cmd(
        cmd=[
            this_python,
            "-c",
            "import sys;print('hello');print('world',file=sys.stderr)",
        ]
    )
    assert "hello" in caplog.text
    assert "world" in caplog.text

    # Capture output
    response = runner.run_cmd(
        cmd=[
            this_python,
            "-c",
            "import sys;print('hello')",
        ],
        capture_output=True,
    )
    assert "hello" in caplog.text
    assert response == "hello"

    # Discard output
    response = runner.run_cmd(
        cmd=[
            this_python,
            "-c",
            "import sys;print('hello')",
        ],
        discard_output=True,
    )
    assert "hello" in caplog.text
    assert "hello" not in response

    # Discard output (with error)
    with pytest.raises(RdkCommandExecutionError):
        runner.run_cmd(
            cmd=[
                this_python,
                "-c",
                "import sys;print('hello\\n');print('world\\n',file=sys.stderr);sys.exit(1)",
            ],
            discard_output=True,
        )
        assert "hello" in caplog.text
        assert "world" in caplog.text
