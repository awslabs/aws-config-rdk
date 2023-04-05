import logging
import logging.handlers
import sys
from pathlib import Path
from typing import List, Optional

import pytest
from colorlog import ColoredFormatter
from pytest_mock import MockerFixture

import rdk.utils.logger as rdk_logger
from rdk import NAME as PKG_NAME


def test__fixup_friendly_name():
    assert rdk_logger._fixup_friendly_name("123") == "123     "
    assert rdk_logger._fixup_friendly_name("12345678") == "12345678"
    assert rdk_logger._fixup_friendly_name("1234567890") == "123456.."


def test__get_log_msg_format():
    assert len(rdk_logger._get_log_msg_format().split(" | ")) == 3

    friendly_name = "xyz"
    msgf = rdk_logger._get_log_msg_format(friendly_name=friendly_name)
    assert len(msgf.split(" | ")) == 4
    assert "asctime" in msgf
    assert "levelname" in msgf
    assert "message" in msgf
    assert friendly_name in msgf


def test__get_colorlog_msg_format():
    assert len(rdk_logger._get_colorlog_msg_format().split(" | ")) == 3

    friendly_name = "xyz"
    msgf = rdk_logger._get_colorlog_msg_format(friendly_name=friendly_name)
    assert len(msgf.split(" | ")) == 4
    assert "asctime" in msgf
    assert "levelname" in msgf
    assert "message" in msgf
    assert "log_color" in msgf
    assert friendly_name in msgf


def test__do_colorlogs(monkeypatch: pytest.MonkeyPatch):
    # NO_COLOR
    with monkeypatch.context() as m:
        m.setattr(sys.stderr, "isatty", lambda: True, raising=False)
        m.setenv("NO_COLOR", "yes")
        assert not rdk_logger._do_colorlogs()

    # TTY
    with monkeypatch.context() as m:
        m.setattr(sys.stderr, "isatty", lambda: False, raising=False)
        m.delenv("NO_COLOR", raising=False)
        assert not rdk_logger._do_colorlogs()

    with monkeypatch.context() as m:
        m.setattr(sys.stderr, "isatty", ValueError("dummy"), raising=False)
        m.delenv("NO_COLOR", raising=False)
        assert not rdk_logger._do_colorlogs()

    # Enabled
    with monkeypatch.context() as m:
        m.setattr(sys.stderr, "isatty", lambda: True, raising=False)
        m.delenv("NO_COLOR", raising=False)
        assert rdk_logger._do_colorlogs()


def test__get_stream_handler():
    assert isinstance(
        rdk_logger._get_stream_handler(friendly_name="xyz"), logging.StreamHandler
    )


def test_init_main_logger():
    logger = rdk_logger.init_main_logger()
    assert isinstance(logger, logging.Logger)
    assert logger.name.startswith(PKG_NAME)
    assert "main" in logger.name
    assert any(isinstance(x, logging.StreamHandler) for x in logger.handlers)
    assert logger.level == logging.DEBUG
    del logger


def test_init_testcase_logger():
    execution_id = "xyz"
    logger = rdk_logger.init_testcase_logger(execution_id=execution_id)
    assert isinstance(logger, logging.Logger)
    assert logger.name.startswith(PKG_NAME)
    assert "rdktest" in logger.name
    assert execution_id in logger.name
    assert any(
        isinstance(x, logging.StreamHandler) and x.level == logging.INFO
        for x in logger.handlers
    )
    assert logger.level == logging.DEBUG
    del logger


def test_add_file_handler(tmp_path: Path):
    logger = rdk_logger.init_main_logger()
    rdk_logger.add_file_handler(logger=logger, logfile_dir=tmp_path)
    assert any(
        isinstance(x, logging.handlers.RotatingFileHandler) for x in logger.handlers
    )
    del logger


def test_update_stream_handler_level():
    logger = rdk_logger.init_main_logger()
    assert any(
        isinstance(x, logging.StreamHandler) and x.level == logging.INFO
        for x in logger.handlers
    )
    rdk_logger.update_stream_handler_level(logger=logger, level=logging.DEBUG)
    assert any(
        isinstance(x, logging.StreamHandler) and x.level == logging.DEBUG
        for x in logger.handlers
    )
    del logger


def test_get_testcase_logger(monkeypatch: pytest.MonkeyPatch):

    with monkeypatch.context() as m:
        logger = rdk_logger.get_testcase_logger()
        assert "unknown" in logger.name
        del logger

    with monkeypatch.context() as m:
        logger = rdk_logger.get_testcase_logger(execution_id="xyz")
        assert "xyz" in logger.name
        del logger

    with monkeypatch.context() as m:
        logger = rdk_logger.get_testcase_logger()
        assert "abc" in logger.name
        del logger


def test_get_main_logger():
    logger = rdk_logger.get_main_logger()
    assert "main" in logger.name
    del logger


def test_logging_formatters_no_color(
    mocker: MockerFixture,
):
    # no color
    mock1 = mocker.patch("rdk.utils.logger._do_colorlogs")
    mock1.return_value = False
    logger = rdk_logger.init_main_logger()
    assert any(
        isinstance(f, logging.Formatter)
        for f in _get_logging_formatters(logger.handlers)
    )


def _get_logging_formatters(handlers: Optional[List[logging.Handler]]):
    formatters = []
    if handlers is not None:
        for h in handlers:
            formatters.append(h.formatter)
    return formatters


def test_logging_formatters_with_color(
    mocker: MockerFixture,
):
    # no color
    mock1 = mocker.patch("rdk.utils.logger._do_colorlogs")
    mock1.return_value = True
    logger = rdk_logger.init_main_logger()
    assert any(
        isinstance(f, ColoredFormatter)
        for f in _get_logging_formatters(logger.handlers)
    )
