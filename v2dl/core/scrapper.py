import re
import time
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Generic, Literal, TypeAlias, TypeVar

from lxml import html

from ..common import BaseConfig, RuntimeConfig, ScrapeError
from ..common.const import BASE_URL
from ..utils import AlbumTracker, LinkParser, Task

# Manage return types of each scraper here
AlbumLink: TypeAlias = str
ImageLinkAndALT: TypeAlias = tuple[str, str]
LinkType = TypeVar("LinkType", AlbumLink, ImageLinkAndALT)
ScrapeType = Literal["album_list", "album_image"]


class ScrapeManager:
    """Manage the starting and ending of the scraper."""

    def __init__(
        self,
        runtime_config: RuntimeConfig,
        base_config: BaseConfig,
        web_bot: Any,
    ) -> None:
        self.runtime_config = runtime_config
        self.base_config = base_config

        self.web_bot = web_bot
        self.dry_run = runtime_config.dry_run
        self.logger = runtime_config.logger

        self.download_service = runtime_config.download_service

    def start_scraping(self) -> None:
        """Start scraping based on URL type."""
        try:
            urls = self._load_urls()
            for url in urls:
                self.runtime_config.url = url
                link_scraper = ScrapeHandler(self.runtime_config, self.base_config, self.web_bot)
                link_scraper.scrape(url, self.dry_run)
        except ScrapeError as e:
            self.logger.exception("Scraping error: '%s'", e)
        finally:
            self.download_service.stop()  # DO NOT REMOVE
            self.web_bot.close_driver()

    def _load_urls(self) -> list[str]:
        """Load URLs from runtime_config (URL or txt file)."""
        if self.runtime_config.input_file:
            with open(self.runtime_config.input_file) as file:
                urls = [line.strip() for line in file if line.strip()]
        else:
            urls = [self.runtime_config.url]
        return urls


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
        runtime_config: RuntimeConfig,
        base_config: BaseConfig,
        web_bot: Any,
    ) -> None:
        self.web_bot = web_bot
        self.logger = runtime_config.logger
        self.runtime_config = runtime_config

        self.strategies: dict[ScrapeType, BaseScraper[Any]] = {
            "album_list": AlbumScraper(
                runtime_config,
                base_config,
                web_bot,
                runtime_config.download_function,
            ),
            "album_image": ImageScraper(
                runtime_config,
                base_config,
                web_bot,
                runtime_config.download_function,
            ),
        }

        self.album_tracker = AlbumTracker(base_config.paths.download_log)
        self.path_parts, self.start_page = LinkParser.parse_input_url(runtime_config.url)

    def scrape(self, url: str, dry_run: bool = False) -> None:
        """Main entry point for scraping operations."""
        scrape_type = self._get_scrape_type()
        if scrape_type == "album_list":
            self.scrape_album_list(url, self.start_page, dry_run)
        else:
            self.scrape_album(url, self.start_page, dry_run)

    def scrape_album_list(self, url: str, start_page: int, dry_run: bool) -> None:
        """Handle scraping of album lists."""
        album_links = self._real_scrape(url, start_page, "album_list")
        self.logger.info("Found %d albums", len(album_links))

        for album_url in album_links:
            if dry_run:
                self.logger.info("[DRY RUN] Album URL: %s", album_url)
            else:
                self.scrape_album(album_url, 1, dry_run)

    def scrape_album(self, album_url: str, start_page: int, dry_run: bool) -> None:
        """Handle scraping of a single album page."""
        if self.album_tracker.is_downloaded(album_url) and not self.runtime_config.no_skip:
            self.logger.info("Album %s already downloaded, skipping.", album_url)
            return

        image_links = self._real_scrape(album_url, start_page, "album_image")
        if not image_links:
            return

        album_name = re.sub(r"\s*\d+$", "", image_links[0][1])
        self.logger.info("Found %d images in album %s", len(image_links), album_name)

        if dry_run:
            for link, _ in image_links:
                self.logger.info("[DRY RUN] Image URL: %s", link)
        else:
            self.album_tracker.log_downloaded(album_url)

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
        strategy.process_page_links(page_links, page_result, tree, page)

        # Check if we've reached the last page
        should_continue = page < LinkParser.get_max_page(tree)
        if not should_continue:
            self.logger.info("Reach last page, stopping")

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

    def _get_scrape_type(self) -> ScrapeType:
        """Get the appropriate handler method based on URL path."""
        for part in self.path_parts:
            if part in self.URL_HANDLERS:
                return self.URL_HANDLERS[part]
        raise ValueError(f"Unsupported URL type: {self.runtime_config.url}")


class BaseScraper(Generic[LinkType], ABC):
    """Abstract base class for different scraping strategies."""

    def __init__(
        self,
        runtime_config: RuntimeConfig,
        base_config: BaseConfig,
        web_bot: Any,
        download_function: Any,
    ) -> None:
        self.runtime_config = runtime_config
        self.base_config = base_config
        self.web_bot = web_bot
        self.download_service = runtime_config.download_service
        self.logger = runtime_config.logger

    @abstractmethod
    def get_xpath(self) -> str:
        """Return xpath for the specific strategy."""

    @abstractmethod
    def process_page_links(
        self,
        page_links: list[str],
        page_result: list[LinkType],
        tree: html.HtmlElement,
        page: int,
        **kwargs: dict[Any, Any],
    ) -> None:
        """Process links found on the page."""


class AlbumScraper(BaseScraper[AlbumLink]):
    """Strategy for scraping album list pages."""

    XPATH_ALBUM_LIST = '//a[@class="media-cover"]/@href'

    def get_xpath(self) -> str:
        return self.XPATH_ALBUM_LIST

    def process_page_links(
        self,
        page_links: list[str],
        page_result: list[AlbumLink],
        tree: html.HtmlElement,
        page: int,
        **kwargs: dict[Any, Any],
    ) -> None:
        page_result.extend([BASE_URL + album_link for album_link in page_links])
        self.logger.info("Found %d albums on page %d", len(page_links), page)


class ImageScraper(BaseScraper[ImageLinkAndALT]):
    """Strategy for scraping album image pages."""

    XPATH_ALBUM = '//div[@class="album-photo my-2"]/img/@data-src'
    XPATH_ALTS = '//div[@class="album-photo my-2"]/img/@alt'

    def __init__(
        self,
        runtime_config: RuntimeConfig,
        base_config: BaseConfig,
        web_bot: Any,
        download_function: Any,
    ) -> None:
        super().__init__(runtime_config, base_config, web_bot, download_function)
        self.dry_run = runtime_config.dry_run
        self.download_function = download_function
        self.alt_counter = 0

    def get_xpath(self) -> str:
        return self.XPATH_ALBUM

    def process_page_links(
        self,
        page_links: list[str],
        page_result: list[ImageLinkAndALT],
        tree: html.HtmlElement,
        page: int,
        **kwargs: dict[Any, Any],
    ) -> None:
        alts: list[str] = tree.xpath(self.XPATH_ALTS)

        # Handle missing alt texts
        # if len(alts) < len(page_links):
        #     missing_alts = [str(i + self.alt_counter) for i in range(len(page_links) - len(alts))]
        #     alts.extend(missing_alts)
        #     self.alt_counter += len(missing_alts)

        page_result.extend(zip(page_links, alts, strict=False))
        _, page_num = LinkParser.parse_input_url(self.runtime_config.url)
        idx = (page_num - 1) * 10 + 1

        # Handle downloads if not in dry run mode
        if not self.dry_run:
            album_name = extract_album_name(alts)

            # assign download job for each image
            for i, (url, _) in enumerate(zip(page_links, alts, strict=False)):
                task_id = f"{album_name}_{i}"
                task = Task(
                    task_id=task_id,
                    func=self.download_function,
                    kwargs={
                        "album_name": task_id,
                        "url": url,
                        "filename": f"{(idx + i):03d}",
                        "base_folder": self.base_config.download.download_dir,
                    },
                )
                self.download_service.add_task(task)

        self.logger.info("Found %d images on page %d", len(page_links), page)


def extract_album_name(alts: list[str]) -> str:
    album_name = next((alt for alt in alts if not alt.isdigit()), None)
    if album_name:
        album_name = re.sub(r"\s*\d*$", "", album_name).strip()
    if not album_name:
        album_name = BASE_URL.rstrip("/").split("/")[-1]
    return album_name
