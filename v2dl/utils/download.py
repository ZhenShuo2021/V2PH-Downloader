import os
import re
import sys
import time
import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from mimetypes import guess_extension
from pathlib import Path

import httpx
from pathvalidate import sanitize_filename
from requests import Response

from .parser import LinkParser
from ..common._types import PathType

logger = logging.getLogger()


class BaseDownloadAPI(ABC):
    """Base protocol for download APIs."""

    def __init__(
        self,
        headers: dict[str, str],
        rate_limit: int,
        no_skip: bool,
        logger: logging.Logger,
    ):
        self.headers = headers
        self.rate_limit = rate_limit
        self.no_skip = no_skip
        self.logger = logger

    @abstractmethod
    def download(self, album_name: str, url: str, filename: str, base_folder: Path) -> bool:
        """Synchronous download method."""
        raise NotImplementedError

    @abstractmethod
    async def download_async(
        self,
        task_id: str,
        url: str,
        filename: str,
        destination: Path,
    ) -> bool:
        """Asynchronous download method."""
        raise NotImplementedError


class ImageDownloadAPI(BaseDownloadAPI):
    """Image download implementation."""

    def download(self, album_name: str, url: str, filename: str, base_folder: Path) -> bool:
        try:
            album_name = album_name.rsplit("_", 1)[0]
            file_path = DownloadPathTool.get_file_dest(base_folder, album_name, filename)
            DownloadPathTool.mkdir(file_path.parent)

            if DownloadPathTool.is_file_exists(file_path, self.no_skip, self.logger):
                return True

            Downloader.download(url, file_path, self.headers, self.rate_limit)
            self.logger.info("Downloaded: '%s'", file_path)
            return True
        except Exception as e:
            self.logger.error("Error in threaded task '%s': %s", url, e)
            return False

    async def download_async(
        self,
        album_name: str,
        url: str,
        filename: str,
        base_folder: Path,
    ) -> bool:
        try:
            album_name = album_name.rsplit("_", 1)[0]
            file_path = DownloadPathTool.get_file_dest(base_folder, album_name, filename)
            DownloadPathTool.mkdir(file_path.parent)

            if DownloadPathTool.is_file_exists(file_path, self.no_skip, self.logger):
                return True

            await Downloader.download_async(url, file_path, self.headers, self.rate_limit)
            self.logger.info("Downloaded: '%s'", file_path)
            return True
        except Exception as e:
            self.logger.error("Error in async task '%s': %s", album_name, e)
            return False


class VideoDownloadAPI(BaseDownloadAPI):
    """Video download implementation."""

    def download(self, task_id: str, url: str, resp: Response, destination: Path) -> bool:
        raise NotImplementedError

    async def download_async(
        self,
        task_id: str,
        url: str,
        resp: Response,
        destination: Path,
    ) -> bool:
        raise NotImplementedError


class ActorDownloadAPI(BaseDownloadAPI):
    """Actor-based download implementation."""

    def download(self, album_name: str, url: str, alt: str, base_folder: Path) -> bool:
        raise NotImplementedError

    async def download_async(self, task_id: str, url: str, alt: str, destination: Path) -> bool:
        raise NotImplementedError


class Downloader:
    """Handles file downloading operations."""

    @staticmethod
    def download(
        url: str,
        save_path: Path,
        headers: dict[str, str] | None,
        speed_limit_kbps: int,
    ) -> None:
        """Download with speed limit."""
        if headers is None:
            headers = {}
        chunk_size = 1024
        speed_limit_bps = speed_limit_kbps * 1024

        timeout = httpx.Timeout(10.0, read=5.0)
        with httpx.Client(timeout=timeout) as client:
            with client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()
                ext = "." + DownloadPathTool.get_ext(response)
                save_path = save_path.with_suffix(ext)

                with open(save_path, "wb") as file:
                    start_time = time.time()
                    downloaded = 0
                    for chunk in response.iter_bytes(chunk_size=chunk_size):
                        file.write(chunk)
                        downloaded += len(chunk)
                        elapsed_time = time.time() - start_time
                        expected_time = downloaded / speed_limit_bps
                        if elapsed_time < expected_time:
                            time.sleep(expected_time - elapsed_time)

    @staticmethod
    async def download_async(
        url: str,
        save_path: Path,
        headers: dict[str, str] | None,
        speed_limit_kbps: int,
    ) -> None:
        """Asynchronous download with speed limit."""
        if headers is None:
            headers = {}
        chunk_size = 1024
        speed_limit_bps = speed_limit_kbps * 1024

        timeout = httpx.Timeout(10.0, read=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()
                ext = "." + DownloadPathTool.get_ext(response)
                save_path = save_path.with_suffix(ext)

                with open(save_path, "wb") as file:
                    start_time = asyncio.get_event_loop().time()
                    downloaded = 0
                    async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                        file.write(chunk)
                        downloaded += len(chunk)
                        elapsed_time = asyncio.get_event_loop().time() - start_time
                        expected_time = downloaded / speed_limit_bps
                        if elapsed_time < expected_time:
                            await asyncio.sleep(expected_time - elapsed_time)


class DownloadPathTool:
    """Handles file and directory operations."""

    @staticmethod
    def mkdir(folder_path: PathType) -> None:
        """Ensure the folder exists, create it if not."""
        Path(folder_path).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def is_file_exists(file_path: PathType, no_skip: bool, logger: logging.Logger) -> bool:
        """Check if the file exists and log the status."""
        if Path(file_path).exists() and not no_skip:
            logger.info("File already exists: '%s'", file_path)
            return True
        return False

    @staticmethod
    def get_file_dest(
        download_root: PathType,
        album_name: str,
        filename: str,
        extension: str | None = None,
    ) -> Path:
        """Construct the file path for saving the downloaded file.

        Args:
            download_root (PathType): The base download folder for v2dl
            album_name (str): The name of the download album, used for the sub-directory
            filename (str): The name of the target download file
            extension (str | None): The file extension of the target download file
        Returns:
            PathType: The full path of the file
        """
        ext = f".{extension}" if extension else ""
        folder = Path(download_root) / sanitize_filename(album_name)
        sf = sanitize_filename(filename)
        return folder / f"{sf}{ext}"

    @staticmethod
    def get_image_ext(url: str, default_ext: str = "jpg") -> str:
        """Get the extension of a URL."""
        image_extensions = r"\.(jpg|jpeg|png|gif|bmp|webp|tiff|svg)(?:\?.*|#.*|$)"
        match = re.search(image_extensions, url, re.IGNORECASE)
        if match:
            # Normalize 'jpeg' to 'jpg'
            return "jpg" if match.group(1).lower() == "jpeg" else match.group(1).lower()
        return default_ext

    @staticmethod
    def get_ext(
        response: httpx.Response,
        default_method: Callable[[str, str], str] | None = None,
    ) -> str:
        """Guess file extension based on response Content-Type."""
        if default_method is None:
            default_method = DownloadPathTool.get_image_ext

        content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
        extension = guess_extension(content_type)
        if extension:
            return extension.lstrip(".")

        return default_method(str(response.url), "jpg")

    @staticmethod
    def check_input_file(input_path: PathType) -> None:
        if input_path and not os.path.isfile(input_path):
            logging.error("Input file %s does not exist.", input_path)
            sys.exit(1)
        else:
            logging.info("Input file %s exists and is accessible.", input_path)


class AlbumTracker:
    """Download log in units of albums."""

    def __init__(self, download_log: str):
        self.album_log_path = download_log

    def is_downloaded(self, album_url: str) -> bool:
        if os.path.exists(self.album_log_path):
            with open(self.album_log_path) as f:
                downloaded_albums = f.read().splitlines()
            return album_url in downloaded_albums
        return False

    def log_downloaded(self, album_url: str) -> None:
        album_url = LinkParser.remove_page_num(album_url)
        if not self.is_downloaded(album_url):
            with open(self.album_log_path, "a") as f:
                f.write(album_url + "\n")


def download_album(
    album_name: str,
    file_links: list[tuple[str, str]],
    destination: str,
    headers: dict[str, str],
    rate_limit: int,
    no_skip: bool,
    logger: logging.Logger,
) -> None:
    """Basic usage example: download files from a list of links."""
    task_manager = ImageDownloadAPI(
        headers=headers,
        rate_limit=rate_limit,
        no_skip=no_skip,
        logger=logger,
    )
    for url, alt in file_links:
        task_id = f"{album_name}_{alt}"
        task_manager.download(task_id, url, alt, Path(destination))
