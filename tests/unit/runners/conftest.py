from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def run_cmd_mock(
    mocker: MockerFixture,
) -> Mock:
    return mocker.patch("rdk.runners.base.BaseRunner.run_cmd")
