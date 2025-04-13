from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic

from lxml import html

from v2dl.common import Config
from v2dl.common.const import BASE_URL, IMAGE_PER_PAGE
from v2dl.scraper.tools import AlbumTracker, DownloadStatus, LogKey, UrlHandler
from v2dl.scraper.types import AlbumResult, ImageResult, PageResultType
from v2dl.utils import DownloadPathTool, Task


class BaseScraper(Generic[PageResultType], ABC):
    """Abstract base class for different scraping strategies."""

    def __init__(
        self,
        config: Config,
        album_tracker: AlbumTracker,
        web_bot: Any,
        download_function: Any,
    ) -> None:
        self.config = config
        self.runtime_config = config.runtime_config
        self.config = config
        self.album_tracker = album_tracker
        self.web_bot = web_bot
        self.download_service = config.runtime_config.download_service
        self.download_function = download_function
        self.logger = config.runtime_config.logger

    @abstractmethod
    def get_xpath(self) -> str:
        """Return xpath of the target ."""

    @abstractmethod
    def process_page_links(
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

    def process_page_links(
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

    def get_xpath(self) -> str:
        return self.XPATH_ALBUM

    def process_page_links(
        self,
        url: str,
        page_links: list[str],
        page_result: list[ImageResult],
        tree: html.HtmlElement,
        page_num: int,
        **kwargs: dict[Any, Any],
    ) -> None:
        is_VIP = False
        alts: list[str] = tree.xpath(self.XPATH_ALTS)
        page_result.extend(zip(page_links, alts, strict=False))

        # check images
        available_images = self.get_available_images(tree)
        idx = (page_num - 1) * IMAGE_PER_PAGE + 1

        # Handle downloads if not in dry run mode
        album_name = UrlHandler.extract_album_name(alts)
        dir_ = self.config.static_config.download_dir

        # assign download job for each image
        page_link_ctr = 0
        for i, available in enumerate(available_images):
            if not available:
                is_VIP = True
                continue
            url = page_links[page_link_ctr]
            page_link_ctr += 1

            filename = f"{(idx + i):03d}"
            dest = DownloadPathTool.get_file_dest(dir_, album_name, filename)

            if not self.config.static_config.dry_run:
                task = Task(
                    task_id=f"{album_name}_{i}",
                    func=self.download_function,
                    kwargs={
                        "url": url,
                        "dest": dest,
                    },
                )
                self.download_service.add_task(task)

        self.logger.info("Found %d images on page %d", len(page_links), page_num)
        album_status = DownloadStatus.VIP if is_VIP else DownloadStatus.OK
        self.album_tracker.update_download_log(
            self.runtime_config.url, {LogKey.status: album_status, LogKey.dest: str(dest.parent)}
        )

    def get_available_images(self, tree: html.HtmlElement) -> list[bool]:
        album_photos = tree.xpath("//div[@class='album-photo my-2']")
        image_status = [False] * len(album_photos)

        for i, photo in enumerate(album_photos):
            if photo.xpath(".//img[@data-src]"):
                image_status[i] = True

        return image_status
