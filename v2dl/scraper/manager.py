import re
from logging import Logger
from typing import TYPE_CHECKING, Any, Generic

from v2dl.common import Config, RuntimeConfig, ScrapeError
from v2dl.scraper.core import (
    AlbumScraper,
    BaseScraper,
    ImageScraper,
)
from v2dl.scraper.tools import AlbumTracker, DownloadStatus, LogKey, MetadataHandler, UrlHandler
from v2dl.scraper.types import PageResultType, ScrapeType

if TYPE_CHECKING:
    from v2dl.web_bot.base import BaseBot


class ScrapeManager:
    """Manage the starting and ending of the scraper."""

    def __init__(
        self,
        config: Config,
        web_bot: "BaseBot",
    ) -> None:
        self.config = config
        self.runtime_config = config.runtime_config
        self.web_bot = web_bot
        self.dry_run = config.static_config.dry_run
        self.logger = config.runtime_config.logger

        self.no_log = False  # flag to not log download status

        self.download_service = config.runtime_config.download_service

        self.album_tracker = AlbumTracker(config.static_config.download_log_path)
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

        self.metadata_handler = MetadataHandler(config, self.album_tracker)

    def start_scraping(self) -> None:
        """Start scraping based on URL type."""
        try:
            urls = UrlHandler.load_urls(self.runtime_config.url, self.runtime_config.url_file)
            if not urls:
                self.logger.info(f"No valid urls found in {self.runtime_config.url_file}")
                self.no_log = True

            for url in urls:
                url = UrlHandler.update_language(url, self.config.static_config.language)
                self.runtime_config.url = url
                self.update_runtime_config(self.runtime_config)
                self.scrape(url, self.dry_run)

                if self.runtime_config.url_file:
                    UrlHandler.mark_processed_url(self.runtime_config.url_file, url)

        except ScrapeError as e:
            self.logger.exception("Scraping error: '%s'", e)
        finally:
            self.download_service.stop()  # DO NOT REMOVE
            if self.config.static_config.terminate:
                self.web_bot.close_driver()

    def scrape(self, url: str, dry_run: bool = False) -> None:
        """Main entry point for scraping operations."""
        scrape_type = UrlHandler.get_scrape_type(self.runtime_config.url)
        if scrape_type is None:
            return

        target_page: int | list[int]
        _, target_page = UrlHandler.parse_input_url(self.runtime_config.url)
        if self.config.static_config.page_range is not None:
            target_page = UrlHandler.parse_page_range(self.config.static_config.page_range)

        if scrape_type == "album_list":
            self.scrape_album_list(url, target_page, dry_run)
        else:
            self.scrape_album(url, target_page, dry_run)

    def scrape_album_list(self, url: str, target_page: int | list[int], dry_run: bool) -> None:
        """Handle scraping of album lists."""
        strategy = self.strategies["album_list"]
        scraper = PageScraper(self.web_bot, strategy, self.logger)

        album_links = scraper.scrape_all_pages(url, target_page)
        self.logger.info("A total of %d albums found for %s", len(album_links), url)

        for album_url in album_links:
            if dry_run:
                self.logger.info("[DRY RUN] Album URL: %s", album_url)
                self.scrape_album(album_url, 1, dry_run)
            else:
                self.scrape_album(album_url, 1, dry_run)

    def scrape_album(self, album_url: str, target_page: int | list[int], dry_run: bool) -> None:
        """Handle scraping of a single album page."""
        clean_url = UrlHandler.remove_query_params(album_url)
        if (
            self.album_tracker.is_downloaded(clean_url)
            and not self.config.static_config.force_download
        ):
            self.logger.info("Album %s already downloaded, skipping.", album_url)
            return

        strategy = self.strategies["album_image"]
        scraper = PageScraper(self.web_bot, strategy, self.logger)

        image_links = scraper.scrape_all_pages(album_url, target_page)
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
            self.album_tracker.log_downloaded(clean_url)

    def update_runtime_config(self, runtime_config: RuntimeConfig) -> None:
        if not isinstance(runtime_config, RuntimeConfig):
            raise TypeError(f"Expected a RuntimeConfig object, got {type(runtime_config).__name__}")
        self.runtime_config = runtime_config

    def log_final_status(self) -> None:
        if self.no_log:
            return

        self.logger.info("Download finished, showing download status")
        download_status = self.album_tracker.get_download_status
        for url, album_status in download_status.items():
            if album_status[LogKey.status] == DownloadStatus.FAIL:
                self.logger.error(f"{url}: Unexpected error")
            elif album_status[LogKey.status] == DownloadStatus.VIP:
                self.logger.warning(f"{url}: VIP images found")
            else:
                self.logger.info(f"{url}: Download successful")

    def write_metadata(self) -> None:
        self.metadata_handler.write_metadata()


class PageScraper(Generic[PageResultType]):
    """Handles the scraping of individual pages."""

    def __init__(
        self,
        web_bot: "BaseBot",
        strategy: BaseScraper[PageResultType],
        logger: Logger,
    ) -> None:
        self.web_bot = web_bot
        self.strategy = strategy
        self.logger = logger

    def scrape_all_pages(self, url: str, target_page: int | list[int]) -> list[Any]:
        """Scrape multiple pages according to target configuration."""
        all_results: list[Any] = []
        page: int | list[int] | None
        page, scrape_one_page = UrlHandler.handle_first_page(target_page)

        scrape_type = "album" if isinstance(self.strategy, AlbumScraper) else "image"
        self.logger.info(
            "Starting to scrape %s links from %s",
            scrape_type,
            url,
        )

        while True:
            page_results, should_continue = self.scrape_page(url, page)
            all_results.extend(page_results)

            page = UrlHandler.handle_pagination(page, target_page)
            if not should_continue or scrape_one_page or page is None:
                break

        return all_results

    def scrape_page(self, url: str, page: int) -> tuple[list[PageResultType], bool]:
        """Scrape a single page and return results and continuation flag."""
        full_url = UrlHandler.add_page_num(url, page)
        html_content = self.web_bot.auto_page_scroll(full_url, page_sleep=0)
        tree = UrlHandler.parse_html(html_content, self.logger)

        if tree is None:
            return [], False

        if self.strategy.is_vip_page(tree):
            _url = UrlHandler.remove_query_params(full_url)
            self.strategy.album_tracker.update_download_log(
                _url, {LogKey.status: DownloadStatus.VIP}
            )
            return [], False

        self.logger.info("Fetching content from %s", full_url)
        page_links = tree.xpath(self.strategy.get_xpath())

        scrape_type = "album_list" if isinstance(self.strategy, AlbumScraper) else "album_image"
        if not page_links:
            self.logger.info(
                "No more %s found on page %d",
                "albums" if scrape_type == "album_list" else "images",
                page,
            )
            return [], False

        page_result: list[PageResultType] = []
        self.strategy.process_page_links(url, page_links, page_result, tree, page)

        # Check if we've reached the last page
        should_continue = page < UrlHandler.get_max_page(tree)
        if not should_continue:
            self.logger.info("Reach last page, stopping")

        return page_result, should_continue
