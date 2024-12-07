import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from v2dl import create_runtime_config
from v2dl.common import BaseConfig, BaseConfigManager
from v2dl.common.const import DEFAULT_CONFIG


@pytest.fixture
def mock_logger():
    return Mock(spec=logging.Logger)


@pytest.fixture
def real_base_config(tmp_path) -> BaseConfig:
    base_config = BaseConfigManager(DEFAULT_CONFIG).load()
    base_config.paths.download_log = tmp_path / "download.log"
    base_config.download.download_dir = tmp_path / "Downloads"
    base_config.download.rate_limit = 1000
    base_config.download.min_scroll_length *= 2
    base_config.download.max_scroll_length = base_config.download.max_scroll_length * 16 + 1
    return base_config


@pytest.fixture
def real_args():
    return SimpleNamespace(
        url="https://www.v2ph.com/album/Weekly-Young-Jump-2012-No29",
        input_file="",
        bot_type="drission",
        chrome_args=[],
        user_agent=None,
        terminate=True,
        dry_run=False,
        concurrency=3,
        force=True,
        use_default_chrome_profile=False,
        directory=None,
        language="ja",
    )


@pytest.fixture
def real_runtime_config(real_args, real_base_config, mock_logger):
    def _create_runtime_config(service_type, log_level):
        return create_runtime_config(
            args=real_args,
            base_config=real_base_config,
            logger=mock_logger,
            log_level=log_level,
            service_type=service_type,
        )

    return _create_runtime_config
