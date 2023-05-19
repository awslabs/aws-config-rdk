import pytest

from rdk import CLI_NAME


@pytest.fixture
def cli_name() -> str:
    return CLI_NAME
