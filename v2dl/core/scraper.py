import re
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Generic, Literal, TypeAlias, TypeVar

from lxml import html

from ..common import ScrapeError
from ..common.const import BASE_URL, IMAGE_PER_PAGE
from ..config import Config, RuntimeConfig
from ..utils import (
    AlbumTracker,
    DownloadLogKeys as LogKey,
    DownloadPathTool,
    DownloadStatus,
    Task,
    count_files,
    enum_to_string,
)
from ..utils.parser import LinkParser

# Manage return types of each scraper here
AlbumLink: TypeAlias = str
ImageLinkAndALT: TypeAlias = tuple[str, str]
LinkType = TypeVar("LinkType", AlbumLink, ImageLinkAndALT)
ScrapeType = Literal["album_list", "album_image"]


class ScrapeManager:
    """Manage the starting and ending of the scraper."""

    def __init__(
        self,
        config: Config,
        web_bot: Any,
    ) -> None:
        self.config = config
        self.runtime_config = config.runtime_config
        self.web_bot = web_bot
        self.dry_run = config.static_config.dry_run
        self.logger = config.runtime_config.logger

        self.no_log = False  # flag to not log download status

        self.download_service = config.runtime_config.download_service
        self.scrape_handler = ScrapeHandler(self.config, self.web_bot)

    def start_scraping(self) -> None:
        """Start scraping based on URL type."""
        try:
            urls = self._load_urls()
            if not urls:
                self.logger.info(f"No valid urls found in {self.runtime_config.url_file}")
                self.no_log = True

            for url in urls:
                url = LinkParser.update_language(url, self.config.static_config.language)
                self.runtime_config.url = url
                self.scrape_handler.update_runtime_config(self.runtime_config)
                self.scrape_handler.scrape(url, self.dry_run)

                if self.runtime_config.url_file:
                    self._mark_urls(url)

        except ScrapeError as e:
            self.logger.exception("Scraping error: '%s'", e)
        finally:
            self.download_service.stop()  # DO NOT REMOVE
            if self.config.static_config.terminate:
                self.web_bot.close_driver()

    def log_final_status(self) -> None:
        if self.no_log:
            return

        self.logger.info("Download finished, showing download status")
        download_status = self.get_download_status
        for url, album_status in download_status.items():
            if album_status[LogKey.status] == DownloadStatus.FAIL:
                self.logger.error(f"{url}: Unexpected error")
            elif album_status[LogKey.status] == DownloadStatus.VIP:
                self.logger.warning(f"{url}: VIP images found")
            else:
                self.logger.info(f"{url}: Download successful")

    def write_metadata(self) -> None:
        if self.config.static_config.no_history:
            return
        download_status = self.get_download_status

        # count real files
        for url, album_status in download_status.items():
            dest = album_status[LogKey.dest]
            real_num = 0 if not dest else count_files(Path(dest))
            self.scrape_handler.album_tracker.update_download_log(url, {LogKey.real_num: real_num})

        # write metadata
        if self.config.path_config.history_file:
            metadata_dest = Path(self.config.path_config.history_file)
        else:
            metadata_name = "metadata_" + str(datetime.now().strftime("%Y%m%d_%H%M%S")) + ".json"
            metadata_dest = Path(self.config.static_config.download_dir) / metadata_name
        metadata_dest.parent.mkdir(parents=True, exist_ok=True)
        with metadata_dest.open("w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    self.get_download_status,
                    indent=4,
                    ensure_ascii=False,
                    default=enum_to_string,
                )
            )

    @property
    def get_download_status(self) -> dict[str, dict[str, Any]]:
        return self.scrape_handler.album_tracker.get_download_status

    def _load_urls(self) -> list[str]:
        """Load URLs from runtime_config (URL or txt file)."""
        if self.runtime_config.url_file:
            with open(self.runtime_config.url_file) as file:
                urls = [line.strip() for line in file if line.strip() and not line.startswith("#")]
        else:
            urls = [self.runtime_config.url]
        return urls

    def _mark_urls(self, target_url: str) -> None:
        with open(self.runtime_config.url_file, "r+") as file:
            lines = file.readlines()
            file.seek(0)

            for line in lines:
                if line.strip().startswith(LinkParser.remove_query_params(target_url)):
                    file.write(f"# {line}")
                else:
                    file.write(line)

            file.truncate()


class ScrapeHandler:
    """Handles all scraper behaviors."""

    # Defines the mapping from url part to scrape method.
    URL_HANDLERS: ClassVar[dict[str, ScrapeType]] = {
        "album": "album_image",
        "actor": "album_list",
        "company": "album_list",
        "category": "album_list",
        "country": "album_list",
    }

    def __init__(
        self,
        config: Config,
        web_bot: Any,
    ) -> None:
        self.config = config
        self.runtime_config = config.runtime_config
        self.logger = config.runtime_config.logger
        self.web_bot = web_bot

        self.album_tracker = AlbumTracker(config.path_config.download_log)
        self.strategies: dict[ScrapeType, BaseScraper[Any]] = {
            "album_list": AlbumScraper(
                config,
                self.album_tracker,
                web_bot,
                config.runtime_config.download_function,
            ),
            "album_image": ImageScraper(
                config,
                self.album_tracker,
                web_bot,
                config.runtime_config.download_function,
            ),
        }

    def scrape(self, url: str, dry_run: bool = False) -> None:
        """Main entry point for scraping operations."""
        if (scrape_type := self._get_scrape_type()) is None:
            return
        _, start_page = LinkParser.parse_input_url(self.runtime_config.url)

        if scrape_type == "album_list":
            self.scrape_album_list(url, start_page, dry_run)
        else:
            self.scrape_album(url, start_page, dry_run)

    def scrape_album_list(self, url: str, start_page: int, dry_run: bool) -> None:
        """Handle scraping of album lists."""
        album_links = self._real_scrape(url, start_page, "album_list")
        self.logger.info("Found %d albums", len(album_links))

        for album_url in album_links:
            if dry_run:
                self.logger.info("[DRY RUN] Album URL: %s", album_url)
                self.scrape_album(album_url, 1, dry_run)
            else:
                self.scrape_album(album_url, 1, dry_run)

    def scrape_album(self, album_url: str, start_page: int, dry_run: bool) -> None:
        """Handle scraping of a single album page."""
        if (
            self.album_tracker.is_downloaded(LinkParser.remove_query_params(album_url))
            and not self.config.static_config.force_download
        ):
            self.logger.info("Album %s already downloaded, skipping.", album_url)
            return

        image_links = self._real_scrape(album_url, start_page, "album_image")
        self.album_tracker.update_download_log(
            self.runtime_config.url,
            {LogKey.expect_num: len(image_links)},
        )
        if not image_links:
            return

        album_name = re.sub(r"\s*\d+$", "", image_links[0][1])
        self.logger.info("Found %d images in album %s", len(image_links), album_name)

        if dry_run:
            for link, _ in image_links:
                self.logger.info("[DRY RUN] Image URL: %s", link)
        else:
            self.album_tracker.log_downloaded(LinkParser.remove_query_params(album_url))

    def update_runtime_config(self, runtime_config: RuntimeConfig) -> None:
        if not isinstance(runtime_config, RuntimeConfig):
            raise TypeError(f"Expected a RuntimeConfig object, got {type(runtime_config).__name__}")
        self.runtime_config = runtime_config

    def _real_scrape(
        self,
        url: str,
        start_page: int,
        scrape_type: ScrapeType,
        **kwargs: dict[Any, Any],
    ) -> list[Any]:
        """Scrapes pages for links using the specified scraping strategy.

        Args:
            url (str): The URL to scrape.
            start_page (int): The starting page number for the scraping process.
            scrape_type (ScrapeType): The type of content to scrape, either "album" or "album_list".
            **kwargs (dict[Any, Any]): Additional keyword arguments for custom behavior.

        Returns:
            list[Any]: A list of results extracted from all scraped pages.

        Raises:
            KeyError: If the provided scrape_type is not found in the strategies.
        """
        strategy = self.strategies[scrape_type]
        self.logger.info(
            "Starting to scrape %s links from %s",
            "album" if scrape_type else "image",
            url,
        )

        all_results: list[Any] = []
        page = start_page

        while True:
            page_results, should_continue = self._scrape_single_page(
                url,
                page,
                strategy,
                scrape_type,
            )
            all_results.extend(page_results)

            if not should_continue:
                break

            page = self._handle_pagination(page)

        return all_results

    def _scrape_single_page(
        self,
        url: str,
        page: int,
        strategy: "BaseScraper[Any]",
        scrape_type: ScrapeType,
    ) -> tuple[list[AlbumLink] | list[ImageLinkAndALT], bool]:
        """Scrapes a single page and retrieves results with a flag indicating whether to continue scraping.

        Args:
            url (str): The URL to scrape.
            page (int): The page number to scrape.
            strategy (BaseScraper[Any]): The scraping strategy that defines how to extract data from the page.
            scrape_type (ScrapeType): The type of content to scrape, either "album" or "album_list".

        Returns:
            tuple[list[AlbumLink] | list[ImageLinkAndALT], bool]: A tuple containing:
            - list[AlbumLink] | list[ImageLinkAndALT]: A list of links or image details extracted from the page.
            - bool: A flag indicating whether to continue to the next page.
        """
        full_url = LinkParser.add_page_num(url, page)
        html_content = self.web_bot.auto_page_scroll(full_url, page_sleep=0)
        tree = LinkParser.parse_html(html_content, self.logger)

        if tree is None:
            return [], False

        # update_download_log for VIP only album
        if strategy.is_vip_page(tree):
            _url = LinkParser.remove_query_params(full_url)
            self.album_tracker.update_download_log(_url, {LogKey.status: DownloadStatus.VIP})
            return [], False

        self.logger.info("Fetching content from %s", full_url)
        page_links = tree.xpath(strategy.get_xpath())

        if not page_links:
            self.logger.info(
                "No more %s found on page %d",
                "albums" if scrape_type == "album_list" else "images",
                page,
            )
            return [], False

        page_result: list[AlbumLink] | list[ImageLinkAndALT] = []
        strategy.process_page_links(url, page_links, page_result, tree, page)

        # Check if we've reached the last page
        should_continue = page < LinkParser.get_max_page(tree)
        if not should_continue:
            self.logger.info("Reach last page, stopping")
            _url = LinkParser.remove_query_params(full_url)

        return page_result, should_continue

    def _handle_pagination(
        self,
        current_page: int,
        max_consecutive_page: int = 3,
        consecutive_sleep: int = 15,
    ) -> int:
        """Handle pagination logic including sleep for consecutive pages."""
        next_page = current_page + 1
        if next_page % max_consecutive_page == 0:
            time.sleep(consecutive_sleep)
        return next_page

    def _get_scrape_type(self) -> ScrapeType | None:
        """Get the appropriate handler method based on URL path."""
        path_parts, _ = LinkParser.parse_input_url(self.runtime_config.url)
        for part in path_parts:
            if part in self.URL_HANDLERS:
                return self.URL_HANDLERS[part]
        self.logger.error(f"Unsupported URL type: {self.runtime_config.url}")
        return None


class BaseScraper(Generic[LinkType], ABC):
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
        page_result: list[LinkType],
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


class AlbumScraper(BaseScraper[AlbumLink]):
    """Strategy for scraping album list pages."""

    XPATH_ALBUM_LIST = '//a[@class="media-cover"]/@href'

    def get_xpath(self) -> str:
        return self.XPATH_ALBUM_LIST

    def process_page_links(
        self,
        url: str,
        page_links: list[str],
        page_result: list[AlbumLink],
        tree: html.HtmlElement,
        page_num: int,
        **kwargs: dict[Any, Any],
    ) -> None:
        page_result.extend([BASE_URL + album_link for album_link in page_links])
        self.logger.info("Found %d albums on page %d", len(page_links), page_num)


class ImageScraper(BaseScraper[ImageLinkAndALT]):
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
        page_result: list[ImageLinkAndALT],
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
        album_name = extract_album_name(alts)
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
            if self.config.static_config.exact_dir:
                dest = DownloadPathTool.get_file_dest(dir_, "", filename)
            else:
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
            self.runtime_config.url,
            {
                LogKey.status: album_status,
                LogKey.dest: str(dest.parent),
            },
        )

    def get_available_images(self, tree: html.HtmlElement) -> list[bool]:
        album_photos = tree.xpath("//div[@class='album-photo my-2']")
        image_status = [False] * len(album_photos)

        for i, photo in enumerate(album_photos):
            if photo.xpath(".//img[@data-src]"):
                image_status[i] = True

        return image_status


def extract_album_name(alts: list[str]) -> str:
    album_name = next((alt for alt in alts if not alt.isdigit()), None)
    if album_name:
        album_name = re.sub(r"\s*\d*$", "", album_name).strip()
    if not album_name:
        album_name = BASE_URL.rstrip("/").split("/")[-1]
    return album_name
