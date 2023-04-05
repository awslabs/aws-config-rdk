import logging
from pathlib import Path

import pytest
from moto import mock_sts

import rdk.utils.logger as rdk_logger

# Silence boto3 logs in tests
for name in ["boto", "urllib3", "s3transfer", "boto3", "botocore", "nose"]:
    logging.getLogger(name).setLevel(logging.CRITICAL)

# Enable debug logs for rdk
logger = rdk_logger.get_main_logger()
rdk_logger.update_stream_handler_level(logger=logger, level=logging.DEBUG)