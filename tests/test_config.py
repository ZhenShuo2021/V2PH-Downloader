import tempfile
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from v2dl import V2DLApp


@pytest.fixture
def default_args():
    """Create default command line arguments with focus on key parameters."""
    return Namespace(
        version=False,
        account=False,
        bot_type="selenium",
        custom_user_agent=None,
        language=None,
        chrome_args=None,
        no_metadata=False,
        force_download=False,
        dry_run=False,
        terminate=False,
        use_default_chrome_profile=False,
        log_level="INFO",
        min_scroll_distance=800,
        max_scroll_distance=1000,
        max_worker=4,
        rate_limit=1.0,
        page_range=None,
        cookies_path=None,
        destination=None,
        metadata_path=None,
        url="https://example.com",
        url_file=None,
    )


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing file paths."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def mock_dependencies():
    """Mock all external dependencies for testing."""
    with (
        patch("v2dl.common.setup_logging") as mock_setup_logging,
        patch("v2dl.utils.create_download_service") as mock_create_download,
        patch("v2dl.web_bot.get_bot") as mock_get_bot,
        patch("v2dl.scraper.ScrapeManager") as mock_scraper,
    ):
        mock_create_download.return_value = (MagicMock(), MagicMock())
        mock_setup_logging.return_value = MagicMock()
        mock_get_bot.return_value = MagicMock()

        yield {
            "setup_logging": mock_setup_logging,
            "create_download": mock_create_download,
            "get_bot": mock_get_bot,
            "scraper": mock_scraper,
        }


@pytest.mark.parametrize(
    "test_param,expected_result",
    [
        # Test force_download flag
        ({"force_download": True}, {"static_config": {"force_download": True}}),
        # Test bot_type
        ({"bot_type": "custom_bot"}, {"static_config": {"bot_type": "custom_bot"}}),
        # Test scroll distance adjustment
        (
            {"min_scroll_distance": 1200, "max_scroll_distance": 800},
            {"static_config": {"min_scroll_distance": 1200, "max_scroll_distance": 2400}},
        ),
    ],
)
def test_flag_and_parameter_configs(default_args, mock_dependencies, test_param, expected_result):
    """Test proper configuration of various flags and parameters."""
    # Setup
    args = default_args
    for key, value in test_param.items():
        setattr(args, key, value)

    app = V2DLApp()
    app._check_cli_inputs = MagicMock()

    # Execute
    app.init(args)

    # Verify
    for config_section, config_values in expected_result.items():
        for key, value in config_values.items():
            assert app.config_manager.get(config_section, key) == value


@pytest.mark.parametrize(
    "test_path_param,expected_config",
    [
        # Test cookies_path
        (
            {"param_name": "cookies_path", "path_value": "test_cookies.txt"},
            {"config_name": "cookies_path"},
        ),
        # Test destination (download_dir)
        ({"param_name": "destination", "path_value": "downloads"}, {"config_name": "download_dir"}),
        # Test cookies_path default (empty string)
        (
            {"param_name": "cookies_path", "path_value": None},
            {"config_name": "cookies_path", "expected_value": ""},
        ),
    ],
)
def test_path_configs(default_args, mock_dependencies, temp_dir, test_path_param, expected_config):
    """Test proper configuration of file and directory paths."""
    # Setup
    args = default_args

    # Set path parameter
    param_name = test_path_param["param_name"]
    path_value = test_path_param["path_value"]

    if path_value is not None:
        full_path = str(temp_dir / path_value)
        setattr(args, param_name, full_path)
    else:
        setattr(args, param_name, None)

    app = V2DLApp()
    app._check_cli_inputs = MagicMock()

    # Execute
    app.init(args)

    # Verify
    config_name = expected_config["config_name"]
    expected_value = expected_config.get(
        "expected_value", full_path if path_value is not None else ""
    )

    assert app.config_manager.get("static_config", config_name) == expected_value
