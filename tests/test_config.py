from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from v2dl.config.config import ConfigManager
from v2dl.config.model import EncryptionConfig, PathConfig, RuntimeConfig, StaticConfig


@pytest.fixture
def default_config():
    return {
        "static_config": {
            "min_scroll_length": 10,
            "max_scroll_length": 100,
            "min_scroll_step": 1,
            "max_scroll_step": 5,
            "max_worker": 4,
            "page_range": None,
            "cookies_path": "",
            "rate_limit": 2,
            "no_metadata": False,
            "language": "en",
            "exact_dir": False,
            "download_dir": "/tests/tmp",
            "force_download": False,
            "chrome_args": [],
            "use_default_chrome_profile": False,
            "dry_run": False,
            "terminate": False,
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
        "path_config": {
            "metadata_path": "/tests/tmp/history.log",
            "download_log_path": "/tests/tmp/download.log",
            "system_log_path": "/tests/tmp/system.log",
            "chrome_exec_path": {
                "Linux": "/tests/tmp/linux/chrome",
                "Darwin": "/tests/tmp/macos/chrome.app",
                "Windows": r"C:\Program Files\tmp\chrome.exe",
            },
            "chrome_profile_path": "/tests/tmp/chrome-profile",
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


def test_initialize_config(default_config):
    """Test default settings"""
    config_manager = ConfigManager(default_config=default_config)
    config_manager.load_from_defaults()
    config = config_manager.initialize_config()

    assert isinstance(config.static_config, StaticConfig)
    assert config.static_config.min_scroll_length == 10
    assert config.static_config.language == "en"

    assert isinstance(config.runtime_config, RuntimeConfig)
    assert config.runtime_config.url == "http://example.com"

    assert isinstance(config.path_config, PathConfig)
    assert config.path_config.metadata_path == "/tests/tmp/history.log"

    assert isinstance(config.encryption_config, EncryptionConfig)
    assert config.encryption_config.key_bytes == 32
    assert config.encryption_config.salt_bytes == 16


def test_load_from_args(default_config, args):
    """Test argparse, it should work with default settings"""
    config_manager = ConfigManager(default_config=default_config)
    config_manager.load_from_defaults()
    config_manager.load_from_args(args)

    static_config = config_manager.create_static_config()
    assert static_config.min_scroll_length == 1500
    assert static_config.max_scroll_length == 2500
    assert static_config.no_metadata is False
    assert static_config.download_dir == Path("/tests/tmp/downloads")
    assert static_config.force_download is True
    assert static_config.dry_run is True
    assert static_config.terminate is True
    assert static_config.chrome_args == ["--headless", "--disable-gpu"]

    runtime_config = config_manager.create_runtime_config()
    assert runtime_config.url == "http://new-url.com"
    assert runtime_config.url_file == "urls.txt"
    assert runtime_config.bot_type == "custom"

    path_config = config_manager.create_path_config()
    assert path_config.metadata_path == "/tests/tmp/new_history.log"


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

runtime_config:
  url: "http://yaml-url.com"
  url_file: "yaml_urls.txt"
  bot_type: "yaml_bot"
  log_level: 10
  user_agent: "yaml-agent"

path_config:
  metadata_path: "/tests/tmp/yaml_history.log"
  download_log_path: "/tests/tmp/yaml_download.log"
  system_log_path: "/tests/tmp/yaml_system.log"
  chrome_exec_path: "/usr/local/bin/yaml-chrome"
  chrome_profile_path: "/tests/tmp/yaml_chrome_profile"

encryption_config:
  key_bytes: 64
  salt_bytes: 32
  nonce_bytes: 24
  kdf_ops_limit: 6
  kdf_mem_limit: 2097152
"""


def test_load_from_yaml(default_config, yaml_config_content):
    config_manager = ConfigManager(default_config=default_config)

    with patch("builtins.open", mock_open(read_data=yaml_config_content)):
        with patch("os.path.exists", return_value=True):
            config_manager.load_from_defaults()
            config_manager.load_from_yaml()

    static_config = config_manager.create_static_config()
    assert static_config.min_scroll_length == 15
    assert static_config.max_scroll_length == 120
    assert static_config.min_scroll_step == 2
    assert static_config.max_scroll_step == 6
    assert static_config.max_worker == 8
    assert static_config.rate_limit == 3
    assert static_config.no_metadata is True
    assert static_config.language == "fr"
    assert static_config.exact_dir is True
    assert static_config.download_dir == "/tests/tmp/yaml_download"
    assert static_config.force_download is True
    assert static_config.chrome_args == ["--no-sandbox", "--disable-dev-shm-usage"]
    assert static_config.use_default_chrome_profile is True
    assert static_config.dry_run is False
    assert static_config.terminate is True

    runtime_config = config_manager.create_runtime_config()
    assert runtime_config.url == "http://yaml-url.com"
    assert runtime_config.url_file == "yaml_urls.txt"
    assert runtime_config.bot_type == "yaml_bot"
    assert runtime_config.log_level == 10
    assert runtime_config.user_agent == "yaml-agent"

    path_config = config_manager.create_path_config()
    assert path_config.metadata_path == "/tests/tmp/yaml_history.log"
    assert path_config.download_log_path == "/tests/tmp/yaml_download.log"
    assert path_config.system_log_path == "/tests/tmp/yaml_system.log"
    assert path_config.chrome_exec_path == "/usr/local/bin/yaml-chrome"
    assert path_config.chrome_profile_path == "/tests/tmp/yaml_chrome_profile"

    encryption_config = config_manager.create_encryption_config()
    assert encryption_config.key_bytes == 64
    assert encryption_config.salt_bytes == 32
    assert encryption_config.nonce_bytes == 24
    assert encryption_config.kdf_ops_limit == 6
    assert encryption_config.kdf_mem_limit == 2097152
