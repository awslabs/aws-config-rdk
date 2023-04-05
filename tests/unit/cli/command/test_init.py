import pytest
from pytest_mock import MockerFixture

from rdk.cli.commands import init as init_cmd


def test_run_exit(mocker: MockerFixture):
    mock1 = mocker.patch("rdk.core.init.RdkInitializer.run")

    with pytest.raises(SystemExit) as exc_info:
        init_cmd.run()
    assert exc_info.type is SystemExit

    mock1.assert_called_once()
