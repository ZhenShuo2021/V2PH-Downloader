import logging
from argparse import Namespace
from unittest.mock import Mock

import pytest

from v2dl.cli.option import parse_arguments
from v2dl.common import Config, ConfigManager
from v2dl.common.const import DEFAULT_CONFIG, DEFAULT_USER_AGENT, HEADERS
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
    config_manager.initialize(real_args[0])

    # setup runtime_config
    config_manager.set("runtime_config", "url", real_arg.url)
    config_manager.set("runtime_config", "download_service", download_service)
    config_manager.set("runtime_config", "download_function", download_function)
    config_manager.set("runtime_config", "logger", mock_logger)
    config_manager.set("runtime_config", "custom_user_agent", DEFAULT_USER_AGENT)

    runtime_config = config_manager.create_runtime_config()
    config_instance = config_manager.initialize(real_arg)
    config_instance.bind_runtime_config(runtime_config)
    return config_instance


@pytest.fixture
def real_args(tmp_path):
    """提供最低需求的命令行參數作整合測試"""
    expected_file_count = 12
    args = [
        "https://www.v2ph.com/album/Weekly-Young-Jump-2012-No29",
        "--min-scroll",
        "5000",
        "--max-scroll",
        "5001",
        "-f",
        "-d",
        str(tmp_path),
    ]
    return parse_arguments(args), expected_file_count


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
