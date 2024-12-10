import logging
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from v2dl import process_input


@pytest.fixture
def logger():
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def args():
    return Namespace(
        version=None,
        input_file=None,
        account=None,
        min_scroll=None,
        max_scroll=None,
        destination=None,
        log_level=logging.WARNING,
    )


@patch("v2dl.config.BaseConfigManager.load")
@patch("v2dl.utils.DownloadPathTool.check_input_file")
def test_process_input_no_version(mock_check_input_file, mock_load, args):
    mock_base_config = MagicMock()
    mock_load.return_value = mock_base_config
    result = process_input(args)
    assert result == mock_base_config
    mock_check_input_file.assert_not_called()


def test_process_input_version(args):
    args.version = True
    with (
        pytest.raises(SystemExit) as e,
        patch("v2dl.version.__version__", "1.0.0"),
        patch("builtins.print") as mock_print,
    ):
        process_input(args)
    mock_print.assert_called_once_with("1.0.0")
    assert e.value.code == 0


@pytest.fixture
def args_valued():
    return Namespace(
        version=None,
        input_file="/path/to/file",
        account="user_account",
        min_scroll=10,
        max_scroll=20,
        destination="/path/to/destination",
        log_level=logging.WARNING,
    )


@patch("v2dl.config.BaseConfigManager.load")
@patch("v2dl.utils.DownloadPathTool.check_input_file")
@patch("v2dl.cli.cli")
def test_process_input_with_values(mock_cli, mock_check_input_file, mock_load, args_valued):
    mock_base_config = MagicMock()
    mock_load.return_value = mock_base_config

    result = process_input(args_valued)

    assert result == mock_base_config
    assert result.download.min_scroll_length == 10
    assert result.download.max_scroll_length == 20
    assert result.download.download_dir == "/path/to/destination"

    mock_check_input_file.assert_called_once_with("/path/to/file")

    mock_cli.assert_called_once_with(mock_base_config.encryption)
