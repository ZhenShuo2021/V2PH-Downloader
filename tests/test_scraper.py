import os
import atexit

# os.environ["GITHUB_ACTIONS"] = "true"
import shutil
import asyncio
import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from v2dl.common.const import VALID_EXTENSIONS
from v2dl.scraper import DownloadStatus, LogKey, ScrapeManager, UrlHandler

TEST_ALBUM_URL = "http://example.com/album"


@pytest.fixture
async def setup_test_env(tmp_path, real_app):
    app = real_app
    app.config.static_config.destination = str(tmp_path)
    try:
        yield app
    finally:
        atexit.unregister(app.scraper.write_metadata)
        download_dir = Path(tmp_path)
        if download_dir.exists():
            shutil.rmtree(download_dir)


@pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") == "true", reason="No GUI on Github")
async def test_download(setup_test_env, real_args):
    args, expected_file_count = real_args
    test_download_dir = Path(args.destination)
    app = setup_test_env
    await asyncio.wait_for(app.run(args), timeout=30)

    # Check directory
    subdirectories = [d for d in test_download_dir.iterdir() if d.is_dir()]
    download_subdir = subdirectories[0]
    assert download_subdir.is_dir(), "Expected a directory but found a file"

    # Check number of files
    image_files = sorted(download_subdir.glob("*"), key=lambda x: x.name)
    image_files = [f for f in image_files if f.suffix.lower()[1:] in VALID_EXTENSIONS]
    assert len(image_files) == expected_file_count, (
        f"Expected {expected_file_count} images, found {len(image_files)}"
    )

    # Check file names match 001, 002, 003...
    for idx, image_file in enumerate(image_files, start=1):
        expected_filename = f"{idx:03d}"
        actual_filename = image_file.stem
        assert expected_filename == actual_filename, (
            f"Expected file name {expected_filename}, found {actual_filename}"
        )

    # Verify image file size
    for image_file in image_files:
        assert image_file.stat().st_size > 0, f"Downloaded image {image_file.name} is empty"


# ===================== Test ScrapeManager =====================


@pytest.fixture
def mock_runtime_config():
    runtime_config = MagicMock()
    runtime_config.url = TEST_ALBUM_URL
    runtime_config.language = "en"
    runtime_config.logger = logging.getLogger()
    runtime_config.url_file = None
    runtime_config.log_level = logging.DEBUG
    return runtime_config


@pytest.fixture
def mock_config(tmp_path):
    config = MagicMock()
    config.static_config.max_worker = 5
    config.paths.download_log_path = tmp_path / "mock_log_path"
    return config


@pytest.fixture
def mock_web_bot():
    web_bot = MagicMock()
    web_bot.close_driver = MagicMock()
    web_bot.auto_page_scroll = MagicMock(return_value="<html></html>")
    return web_bot


@pytest.fixture
def real_scrape_manager(mock_config, mock_web_bot):
    return ScrapeManager(mock_config, mock_web_bot)


def test_load_urls(tmp_path):
    test_file = tmp_path / "input_urls.txt"
    test_file.write_text(f"{TEST_ALBUM_URL}1\n{TEST_ALBUM_URL}2\n")

    urls_from_file = UrlHandler.load_urls(url="", url_file=str(test_file))
    assert urls_from_file == [TEST_ALBUM_URL + "1", TEST_ALBUM_URL + "2"]

    urls_direct = UrlHandler.load_urls(url=TEST_ALBUM_URL, url_file=None)
    assert urls_direct == [TEST_ALBUM_URL]

    if os.name != "nt":
        shutil.rmtree(tmp_path)


def test_log_final_status(real_scrape_manager):
    url1, url2, url3 = TEST_ALBUM_URL + "1", TEST_ALBUM_URL + "2", TEST_ALBUM_URL + "3"
    mock_status = {
        url1: {LogKey.status: DownloadStatus.OK},
        url2: {LogKey.status: DownloadStatus.FAIL},
        url3: {LogKey.status: DownloadStatus.VIP},
    }
    for k, v in mock_status.items():
        real_scrape_manager.album_tracker.update_download_log(k, v)
        real_scrape_manager.processed_urls.add(k)
    real_scrape_manager.logger.info = MagicMock()
    real_scrape_manager.logger.error = MagicMock()
    real_scrape_manager.logger.warning = MagicMock()

    real_scrape_manager.log_final_status()

    real_scrape_manager.logger.info.assert_any_call("Download finished, showing download status")
    real_scrape_manager.logger.info.assert_any_call(f"{url1}: Download successful")
    real_scrape_manager.logger.error.assert_called_once_with(f"{url2}: Unexpected error")
    real_scrape_manager.logger.warning.assert_called_once_with(f"{url3}: VIP images found")
