import shutil
import logging
from pathlib import Path
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
    def setup_env(service_type) -> tuple[ScrapeHandler, BaseConfig, RuntimeConfig, int]:
        log_level = logging.INFO
        logger = setup_logging(log_level, logger_name="pytest", archive=False)
        expected_file_count = 12

        args = SimpleNamespace(
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

        runtime_config = create_runtime_config(
            args=args,  # type: ignore
            base_config=base_config,
            logger=logger,
            log_level=log_level,
            service_type=service_type,
        )

        web_bot = get_bot(runtime_config, base_config)
        scraper = ScrapeHandler(runtime_config, base_config, web_bot)

        return scraper, base_config, runtime_config, expected_file_count

    try:
        yield setup_env
    finally:
        download_dir = tmp_path / "Downloads"
        download_log = tmp_path / "download.log"
        if download_dir.exists():
            shutil.rmtree(download_dir)
        if download_log.exists():
            download_log.unlink()


def test_download_sync(setup_test_env):
    scraper: ScrapeHandler
    base_config: BaseConfig
    runtime_config: RuntimeConfig
    valid_extensions = (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG")

    setup_env = setup_test_env
    scraper, base_config, runtime_config, expected_file_count = setup_env(ServiceType.ASYNC)
    test_download_dir = Path(base_config.download.download_dir)

    scraper.scrape(runtime_config.url)
    runtime_config.download_service.stop(30)

    # Check directory
    subdirectories = [d for d in test_download_dir.iterdir() if d.is_dir()]
    download_subdir = subdirectories[0]
    assert download_subdir.is_dir(), "Expected a directory but found a file"

    # Check number of files
    image_files = sorted(download_subdir.glob("*"), key=lambda x: x.name)
    image_files = [f for f in image_files if f.suffix.lower() in valid_extensions]
    assert len(image_files) == expected_file_count, (
        f"Expected {expected_file_count} images, found {len(image_files)}"
    )

    # Check file names match 001, 002, 003... 013
    for idx, image_file in enumerate(image_files, start=1):
        expected_filename = f"{idx:03d}"
        actual_filename = image_file.stem
        assert expected_filename == actual_filename, (
            f"Expected file name {expected_filename}, found {actual_filename}"
        )

    # Verify image file size
    for image_file in image_files:
        assert image_file.stat().st_size > 0, f"Downloaded image {image_file.name} is empty"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
