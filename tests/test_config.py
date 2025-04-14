from argparse import Namespace
from unittest.mock import MagicMock, mock_open, patch

import pytest

from v2dl.common.config import ConfigManager


@pytest.fixture
def default_config():
    return {
        "static_config": {
            "min_scroll_length": 10,
            "max_scroll_length": 100,
            "min_scroll_step": 1,
            "max_scroll_step": 5,
            "max_worker": 4,
            "rate_limit": 2,
            "page_range": None,
            "no_metadata": False,
            "force_download": False,
            "dry_run": False,
            "terminate": False,
            "language": "en",
            "chrome_args": "",
            "use_default_chrome_profile": False,
            "exact_dir": False,
            # path relative configurations
            "cookies_path": "",
            "download_dir": "/tests/tmp",
            "download_log_path": "/tests/tmp/download.log",
            "metadata_path": "/tests/tmp/history.log",
            "system_log_path": "/tests/tmp/system.log",
            "chrome_exec_path": {
                "Linux": "/tests/tmp/linux/chrome",
                "Darwin": "/tests/tmp/macos/chrome.app",
                "Windows": r"C:\Program Files\tmp\chrome.exe",
            },
            "chrome_profile_path": "/tests/tmp/chrome-profile",
        },
        "runtime_config": {
            "url": "http://example.com",
            "url_file": "",
            "bot_type": "default",
            "download_service": None,
            "download_function": None,
            "logger": MagicMock(),
            "log_level": 20,
            "custom_user_agent": "test-agent",
        },
        "encryption_config": {
            "key_bytes": 32,
            "salt_bytes": 16,
            "nonce_bytes": 12,
            "kdf_ops_limit": 4,
            "kdf_mem_limit": 2**20,
        },
    }


@pytest.fixture
def yaml_config_content():
    return """
static_config:
  min_scroll_length: 15
  language: "fr"
runtime_config:
  url: "http://yaml-url.com"
encryption_config:
  key_bytes: 64
"""


def test_initialize_config_order(default_config, yaml_config_content):
    with patch("builtins.open", mock_open(read_data=yaml_config_content)):
        with patch("os.path.exists", return_value=True):
            cli_args = Namespace(
                url="http://cli-url.com",
                min_scroll=20,
                quiet=True,
                destination=None,
                directory=None,
                chrome_args="",
                force_download=True,
            )
            config_manager = ConfigManager(default_config=default_config)
            config = config_manager.initialize_config(cli_args)
            runtime_config = config_manager.create_runtime_config()
            config.bind_runtime_config(runtime_config)

            # 檢查是否按照 CLI > YAML > DEFAULTS
            assert config.runtime_config.url == "http://cli-url.com"  # CLI
            assert config.static_config.min_scroll_length == 20  # CLI
            assert config.static_config.language == "fr"  # YAML
            assert config.encryption_config.key_bytes == 64  # YAML
