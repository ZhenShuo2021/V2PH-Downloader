from argparse import Namespace
from unittest.mock import MagicMock, mock_open, patch

import pytest

from v2dl.config.config import ConfigManager
from v2dl.config.model import EncryptionConfig, RuntimeConfig, StaticConfig


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
            "chrome_args": [],
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
            "user_agent": "test-agent",
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
  max_scroll_length: 120
  min_scroll_step: 2
  max_scroll_step: 6
  max_worker: 8
  rate_limit: 3
  no_metadata: true
  language: "fr"
  exact_dir: true
  download_dir: "/tests/tmp/yaml_download"
  force_download: true
  chrome_args:
    - "--no-sandbox"
    - "--disable-dev-shm-usage"
  use_default_chrome_profile: true
  dry_run: false
  terminate: true
  metadata_path: "/tests/tmp/yaml_history.log"
  download_log_path: "/tests/tmp/yaml_download.log"
  system_log_path: "/tests/tmp/yaml_system.log"
  chrome_exec_path: "/usr/local/bin/yaml-chrome"
  chrome_profile_path: "/tests/tmp/yaml_chrome_profile"

runtime_config:
  url: "http://yaml-url.com"
  url_file: "yaml_urls.txt"
  bot_type: "yaml_bot"
  log_level: 10
  user_agent: "yaml-agent"

encryption_config:
  key_bytes: 64
  salt_bytes: 32
  nonce_bytes: 24
  kdf_ops_limit: 6
  kdf_mem_limit: 2097152
"""


@pytest.fixture
def args():
    """fixture for user input arguments"""
    return Namespace(
        url="http://new-url.com",
        url_file="urls.txt",
        bot_type="custom",
        cookies_path="/Users/leo/.config/v2dl",
        language="en",
        destination="/tests/tmp/downloads",
        directory=None,
        no_metadata=False,
        metadata_path="/tests/tmp/new_history.log",
        force_download=True,
        min_scroll=1500,
        max_scroll=2500,
        page_range=None,
        dry_run=True,
        terminate=True,
        chrome_args="--headless//--disable-gpu",
        use_default_chrome_profile=False,
        quiet=False,
        verbose=True,
        log_level=None,
    )


def test_initialize_config(default_config, yaml_config_content, args):
    """Test default settings"""
    config_manager = ConfigManager(default_config=default_config)

    # create test config
    with patch("builtins.open", mock_open(read_data=yaml_config_content)):
        with patch("os.path.exists", return_value=True):
            config = config_manager.initialize_config(args)
    runtime_config = config_manager.create_runtime_config()
    config.bind_runtime_config(runtime_config)

    assert isinstance(config.static_config, StaticConfig)
    assert config.static_config.min_scroll_length == 1500
    assert config.static_config.language == "en"

    assert isinstance(config.runtime_config, RuntimeConfig)
    assert config.runtime_config.url == "http://new-url.com"

    assert isinstance(config.encryption_config, EncryptionConfig)
    assert config.encryption_config.key_bytes == 64
    assert config.encryption_config.salt_bytes == 32
