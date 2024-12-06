import os
import shutil
import logging
from types import SimpleNamespace

import pytest

from v2dl import create_runtime_config
from v2dl.common import BaseConfigManager, setup_logging
from v2dl.common._types import BaseConfig, RuntimeConfig
from v2dl.common.const import DEFAULT_CONFIG
from v2dl.core import ScrapeHandler
from v2dl.utils import ServiceType
from v2dl.web_bot import get_bot


@pytest.fixture
def base_config(tmp_path) -> BaseConfig:
    base_config = BaseConfigManager(DEFAULT_CONFIG).load()
    base_config.paths.download_log = tmp_path / "download.log"
    base_config.download.download_dir = tmp_path / "Downloads"
    base_config.download.rate_limit = 1000
    base_config.download.min_scroll_length *= 2
    base_config.download.max_scroll_length = base_config.download.max_scroll_length * 16 + 1
    return base_config


@pytest.fixture
def setup_test_env(tmp_path, base_config):
    def setup_env(service_type) -> tuple[ScrapeHandler, BaseConfig, RuntimeConfig]:
        log_level = logging.INFO
        logger = setup_logging(log_level, logger_name="pytest", archive=False)

        args = SimpleNamespace(
            url="https://www.v2ph.com/album/Weekly-Big-Comic-Spirits-2016-No22-23",
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

        runtime_config = create_runtime_config(
            args=args,  # type: ignore
            base_config=base_config,
            logger=logger,
            log_level=log_level,
            service_type=service_type,
        )

        web_bot = get_bot(runtime_config, base_config)
        scraper = ScrapeHandler(runtime_config, base_config, web_bot)

        return scraper, base_config, runtime_config

    try:
        yield setup_env
    finally:
        download_dir = tmp_path / "Downloads"
        download_log = tmp_path / "download.log"
        if download_dir.exists():
            shutil.rmtree(download_dir)
        if download_log.exists():
            download_log.unlink()


@pytest.mark.parametrize("service_type", [ServiceType.ASYNC, ServiceType.THREADING])
def test_download_sync(setup_test_env, service_type):
    scraper: ScrapeHandler
    base_config: BaseConfig
    runtime_config: RuntimeConfig
    valid_extensions = (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG")

    setup_env = setup_test_env
    scraper, base_config, runtime_config = setup_env(service_type)
    test_download_dir = base_config.download.download_dir

    single_page_result, _ = scraper._scrape_single_page(
        runtime_config.url,
        1,
        scraper.strategies["album_image"],
        "album_image",
    )

    assert isinstance(single_page_result, list), "Single page result should be a list"
    assert len(single_page_result) > 0, "Single page should return some results"
    runtime_config.download_service.stop(30)

    # Verify directory structure
    assert os.path.exists(test_download_dir), "Download directory not created"
    subdirectories = [
        d
        for d in os.listdir(test_download_dir)
        if os.path.isdir(os.path.join(test_download_dir, d))
    ]

    assert len(subdirectories) > 0, "No subdirectory found"

    # Verify downloaded content
    download_subdir = os.path.join(test_download_dir, subdirectories[0])
    assert os.path.isdir(download_subdir), "Expected a directory but found a file"

    # Check for downloaded images
    image_files = [
        f for f in os.listdir(download_subdir) if any(f.endswith(ext) for ext in valid_extensions)
    ]
    image_files_exist = len(image_files) > 0

    assert image_files_exist, "No image found"

    # Verify image file
    if image_files_exist:
        test_image = os.path.join(download_subdir, image_files[0])
        assert os.path.getsize(test_image) > 0, "Downloaded image is empty"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
