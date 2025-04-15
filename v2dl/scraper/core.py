import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic

import httpx
from lxml import html

from v2dl.common import Config
from v2dl.common.const import BASE_URL, HEADERS, IMAGE_PER_PAGE
from v2dl.scraper.downloader import DirectoryCache, DownloadPathTool
from v2dl.scraper.tools import AlbumTracker, DownloadStatus, LogKey, UrlHandler
from v2dl.scraper.types import AlbumResult, ImageResult, PageResultType


class BaseScraper(Generic[PageResultType], ABC):
    """Abstract base class for different scraping strategies."""

    def __init__(
        self,
        config: Config,
        album_tracker: AlbumTracker,
    ) -> None:
        self.config = config
        self.runtime_config = config.runtime_config
        self.config = config
        self.album_tracker = album_tracker
        self.logger = config.runtime_config.logger

    @abstractmethod
    def get_xpath(self) -> str:
        """Return xpath of the target ."""

    @abstractmethod
    async def process_page_links(
        self,
        url: str,
        page_links: list[str],
        page_result: list[PageResultType],
        tree: html.HtmlElement,
        page_num: int,
        **kwargs: dict[Any, Any],
    ) -> None:
        """Process links found on the page.

        Note that different strategy has different types of page_result.

        Args:
            page_links (list[str]): The pre-processed result list, determined by get_xpath, used for page_result
            page_result (list[LinkType]): The real result of scraping.
            tree (html.HtmlElement): The xpath tree of the current page.
            page_num (int): The page number of the current URL.
        """

    def is_vip_page(self, tree: html.HtmlElement) -> bool:
        return bool(
            tree.xpath(
                '//div[contains(@class, "alert") and contains(@class, "alert-warning")]//a[contains(@href, "/user/upgrade")]',
            ),
        )


class AlbumScraper(BaseScraper[AlbumResult]):
    """Strategy for scraping album list pages."""

    XPATH_ALBUM_LIST = '//a[@class="media-cover"]/@href'

    def get_xpath(self) -> str:
        return self.XPATH_ALBUM_LIST

    async def process_page_links(
        self,
        url: str,
        page_links: list[str],
        page_result: list[AlbumResult],
        tree: html.HtmlElement,
        page_num: int,
        **kwargs: dict[Any, Any],
    ) -> None:
        page_result.extend([BASE_URL + album_link for album_link in page_links])
        self.logger.info("Found %d albums on page %d", len(page_links), page_num)


class ImageScraper(BaseScraper[ImageResult]):
    """Strategy for scraping album image pages."""

    XPATH_ALBUM = '//div[@class="album-photo my-2"]/img/@data-src'
    XPATH_ALTS = '//div[@class="album-photo my-2"]/img/@alt'
    XPATH_VIP = ""

    def __init__(self, config: Config, album_tracker: AlbumTracker) -> None:
        super().__init__(config, album_tracker)
        self.cache = DirectoryCache()

    def get_xpath(self) -> str:
        return self.XPATH_ALBUM

    async def download_file(self, url: str, dest: Path) -> bool:
        if DownloadPathTool.is_file_exists(
            dest, self.config.static_config.force_download, self.cache, self.logger
        ):
            self.logger.info("File exists: '%s'", dest)
            return True

        try:
            DownloadPathTool.mkdir(dest.parent)
            limits = httpx.Limits(
                max_keepalive_connections=self.config.static_config.max_worker,
                max_connections=self.config.static_config.max_worker * 2,
            )

            async with httpx.AsyncClient(
                headers=HEADERS,
                http2=True,
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                limits=limits,
            ) as client:
                async with client.stream("GET", url, headers=HEADERS) as response:
                    response.raise_for_status()
                    ext = "." + DownloadPathTool.get_ext(response)
                    dest = dest.with_suffix(ext)

                    with open(dest, "wb") as f:
                        speed_limit_kbps = self.config.static_config.rate_limit
                        total_bytes = 0
                        start_time = asyncio.get_running_loop().time()
                        chunk_size = 8192

                        async for chunk in response.aiter_bytes(chunk_size):
                            f.write(chunk)

                            if speed_limit_kbps:
                                total_bytes += len(chunk)
                                expected_time = total_bytes / (speed_limit_kbps * 1024)
                                elapsed_time = abs(asyncio.get_running_loop().time() - start_time)

                                if elapsed_time < expected_time:
                                    await asyncio.sleep(expected_time - elapsed_time)

            self.logger.info("Downloaded: '%s'", dest)
            return True
        except Exception as e:
            self.logger.error("Error downloading '%s': %s", dest, e)
            return False

    async def process_page_links(
        self,
        url: str,
        page_links: list[str],
        page_result: list[ImageResult],
        tree: html.HtmlElement,
        page_num: int,
        **kwargs: dict[Any, Any],
    ) -> None:
        """The input `url` is the album's url, not image url"""
        is_VIP = False
        alts: list[str] = tree.xpath(self.XPATH_ALTS)
        page_result.extend(zip(page_links, alts, strict=False))

        available_images = self.get_available_images(tree)
        idx = (page_num - 1) * IMAGE_PER_PAGE + 1

        album_name = UrlHandler.extract_album_name(alts)
        dir_ = self.config.static_config.download_dir

        download_tasks = []
        download_paths = []
        page_link_ctr = 0
        for i, available in enumerate(available_images):
            if not available:
                is_VIP = True
                continue
            if page_link_ctr >= len(page_links):
                break
            image_url = page_links[page_link_ctr]
            page_link_ctr += 1

            filename = f"{(idx + i):03d}"
            dest = DownloadPathTool.get_file_dest(dir_, album_name, filename)
            download_tasks.append(self.download_file(image_url, dest))
            download_paths.append(dest)

        if download_tasks:
            download_results = await asyncio.gather(*download_tasks)

            successful_downloads = sum(1 for result in download_results if result)
            failed_downloads = len(download_results) - successful_downloads

            if failed_downloads > 0:
                self.logger.warning("Failed to download %d images", failed_downloads)

        self.logger.info("Found %d images on page %d", len(page_links), page_num)

        destination = download_paths[0].parent if download_paths else Path(dir_) / album_name

        album_status = DownloadStatus.VIP if is_VIP else DownloadStatus.OK
        clean_url = UrlHandler.remove_query_params(url)
        self.album_tracker.update_download_log(
            clean_url, {LogKey.status: album_status, LogKey.dest: str(destination)}
        )

    def get_available_images(self, tree: html.HtmlElement) -> list[bool]:
        album_photos = tree.xpath("//div[@class='album-photo my-2']")
        image_status = [False] * len(album_photos)

        for i, photo in enumerate(album_photos):
            if photo.xpath(".//img[@data-src]"):
                image_status[i] = True

        return image_status
