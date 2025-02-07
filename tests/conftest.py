import logging
from argparse import Namespace
from unittest.mock import Mock

import pytest

from v2dl.common import Config, ConfigManager
from v2dl.common.const import DEFAULT_CONFIG, HEADERS, SELENIUM_AGENT
from v2dl.utils.factory import ServiceType, create_download_service


@pytest.fixture
def real_config(tmp_path, real_download_service, real_args, mock_logger) -> Config:
    real_arg = real_args[0]
    config_manager = ConfigManager(DEFAULT_CONFIG)
    download_service, download_function = real_download_service(ServiceType.ASYNC)
    # prepare runtime_config
    download_service, download_function = create_download_service(
        Namespace(force_download=True),
        config_manager.get("static_config", "max_worker"),
        config_manager.get("static_config", "rate_limit"),
        mock_logger,
        HEADERS,
    )
    # setup static_config
    config_manager.set("static_config", "download_dir", str(tmp_path / "Downloads"))
    config_manager.set("static_config", "rate_limit", 10000)
    config_manager.set("static_config", "min_scroll_length", 2000)
    config_manager.set("static_config", "max_scroll_length", 4000)
    config_manager.set("static_config", "page_range", None)
    config_manager.set("static_config", "download_log_path", str(tmp_path / "download.log"))
    config_manager.set("static_config", "chrome_profile_path", str(tmp_path / "chrome_profile"))
    config_manager.initialize_config(real_args[0])

    # setup runtime_config
    config_manager.set("runtime_config", "url", real_arg.url)
    config_manager.set("runtime_config", "download_service", download_service)
    config_manager.set("runtime_config", "download_function", download_function)
    config_manager.set("runtime_config", "logger", mock_logger)
    config_manager.set("runtime_config", "user_agent", SELENIUM_AGENT)

    runtime_config = config_manager.create_runtime_config()
    config_instance = config_manager.initialize_config(real_arg)
    config_instance.bind_runtime_config(runtime_config)
    return config_instance


@pytest.fixture
def real_args(tmp_path):
    expected_file_count = 12
    return Namespace(
        url="https://www.v2ph.com/album/Weekly-Young-Jump-2012-No29",
        input_file="",
        bot_type="drissionpage",
        cookies_path="",
        chrome_args=[],
        page_range=None,
        user_agent=None,
        terminate=True,
        dry_run=False,
        concurrency=3,
        metadata_path="",
        no_metadata=False,
        force_download=True,
        use_default_chrome_profile=False,
        directory=None,
        language="ja",
        url_file="urls.txt",
        destination=tmp_path,
        min_scroll=1500,
        max_scroll=2500,
        quiet=False,
        verbose=True,
        log_level=None,
    ), expected_file_count


@pytest.fixture
def real_download_service(real_args, mock_logger):
    args, _ = real_args

    def _create_download_service(service_type):
        return create_download_service(
            args=args,
            max_worker=5,
            rate_limit=400,
            logger=mock_logger,
            headers=HEADERS,
            service_type=service_type,
        )

    return _create_download_service


@pytest.fixture
def mock_logger():
    return Mock(spec=logging.Logger)
