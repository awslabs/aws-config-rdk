import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

import colorlog

from rdk import NAME as PKG_NAME

LOGFILE_NAME = "rdk.log"
LOG_DATE_FMT = "%Y-%m-%dT%H:%M:%S%z"
LOG_COLORS = {
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold_red",
}


def _fixup_friendly_name(thing: str) -> str:
    if len(thing) < 8:
        return thing.ljust(8)
    if len(thing) > 8:
        return thing[:6] + ".."
    return thing


def _get_log_msg_format(friendly_name: Optional[str] = None) -> str:
    components = [
        "%(asctime)s",
        "%(levelname)-8s",
        "%(message)s",
    ]
    if friendly_name:
        components.insert(2, _fixup_friendly_name(friendly_name))
    return " | ".join(components)


def _get_colorlog_msg_format(friendly_name: Optional[str] = None) -> str:
    components = [
        "%(thin)s%(asctime)s%(reset)s",
        "%(log_color)s%(levelname)-8s%(reset)s",
        "%(message)s",
    ]
    if friendly_name:
        components.insert(
            2,
            "%(thin_purple)s" + _fixup_friendly_name(friendly_name) + "%(reset)s",
        )
    return " | ".join(components)


def _do_colorlogs() -> bool:
    # Check TTY
    isa_tty = False
    try:
        if sys.stderr.isatty():
            isa_tty = True
    except Exception:
        isa_tty = False
    if not isa_tty:
        return False

    # Check if NO_COLOR is requested (https://no-color.org/)
    no_color = os.getenv("NO_COLOR", default="").lower()
    if no_color and no_color in ["yes", "y", "true", "on", "1"]:
        return False

    # Enable colors
    return True


def _get_stream_handler(friendly_name: Optional[str] = None) -> logging.StreamHandler:
    # Build formatters
    log_formatter = logging.Formatter(
        fmt=_get_log_msg_format(friendly_name=friendly_name),
        datefmt=LOG_DATE_FMT,
    )

    # Colors?
    if _do_colorlogs():
        log_formatter = colorlog.ColoredFormatter(
            fmt=_get_colorlog_msg_format(friendly_name=friendly_name),
            datefmt=LOG_DATE_FMT,
            reset=True,
            log_colors=LOG_COLORS,
        )

    # Build stream handler
    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(log_formatter)
    stderr_handler.setLevel(logging.INFO)

    return stderr_handler


def init_main_logger() -> logging.Logger:
    """
    Initialize main logger.
    """
    friendly_name = "main"
    logger = logging.getLogger(f"{PKG_NAME}.cli.{friendly_name}")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.NullHandler())
    logger.addHandler(_get_stream_handler(friendly_name=friendly_name))
    return logger


def add_file_handler(logger: logging.Logger, logfile_dir: Path):
    """
    Add a file handler to an existing logger once the location is known.
    """
    friendly_name = logger.name.split(".")[-1]
    logfile_dir.mkdir(parents=True, exist_ok=True)

    logfile_formatter = logging.Formatter(
        fmt=_get_log_msg_format(friendly_name=friendly_name),
        datefmt=LOG_DATE_FMT,
    )

    file_handler = logging.handlers.RotatingFileHandler(
        filename=(logfile_dir / LOGFILE_NAME),
        mode="a",
        encoding="utf-8",
        maxBytes=10485760,  # 10mb
        backupCount=10,
    )
    file_handler.setFormatter(logfile_formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)


def update_stream_handler_level(logger: logging.Logger, level: int):
    """
    Dynamically update log levels for a stream handler.
    """
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setLevel(level)


def get_main_logger() -> logging.Logger:
    """
    Return main logger.
    """
    friendly_name = "main"
    return logging.getLogger(f"{PKG_NAME}.cli.{friendly_name}")
