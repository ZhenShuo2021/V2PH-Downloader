import os
import re
import sys
import time
import asyncio
import logging
from abc import ABC, abstractmethod
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from mimetypes import guess_extension
from pathlib import Path
from typing import Any

import httpx
from pathvalidate import sanitize_filename

from .parser import LinkParser
from ..common._types import PathType

logger = logging.getLogger()


class BaseDownloadAPI(ABC):
    """Base protocol for download APIs."""

    def __init__(
        self,
        headers: dict[str, str],
        rate_limit: int,
        force_download: bool,
        cache: "DirectoryCache",
    ):
        self.headers = headers
        self.rate_limit = rate_limit
        self.force_download = force_download
        self.logger = logger
        self.cache = cache

    @abstractmethod
    def download(self, url: str, dest: Path) -> bool:
        """Synchronous download method."""
        raise NotImplementedError

    @abstractmethod
    async def download_async(self, url: str, dest: Path) -> bool:
        """Asynchronous download method."""
        raise NotImplementedError


class ImageDownloadAPI(BaseDownloadAPI):
    """Image download implementation."""

    def download(self, url: str, dest: Path) -> bool:
        if DownloadPathTool.is_file_exists(dest, self.force_download, self.cache, self.logger):
            return True
        try:
            DownloadPathTool.mkdir(dest.parent)
            Downloader.download(url, dest, self.headers, self.rate_limit)
            self.logger.info("Downloaded: '%s'", dest)
            return True
        except Exception as e:
            self.logger.error("Error in threaded task '%s': %s", url, e)
            return False

    async def download_async(self, url: str, dest: Path) -> bool:
        if DownloadPathTool.is_file_exists(dest, self.force_download, self.cache, self.logger):
            return True
        try:
            DownloadPathTool.mkdir(dest.parent)
            await Downloader.download_async(url, dest, self.headers, self.rate_limit)
            self.logger.info("Downloaded: '%s'", dest)
            return True
        except Exception as e:
            self.logger.error("Error in async task '%s': %s", url, e)
            return False


class VideoDownloadAPI(BaseDownloadAPI):
    """Video download implementation."""

    def download(self, url: str, dest: Path) -> bool:
        raise NotImplementedError

    async def download_async(self, url: str, dest: Path) -> bool:
        raise NotImplementedError


class ActorDownloadAPI(BaseDownloadAPI):
    """Actor-based download implementation."""

    def download(self, url: str, dest: Path) -> bool:
        raise NotImplementedError

    async def download_async(self, url: str, dest: Path) -> bool:
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
    def is_file_exists(
        file_path: PathType,
        force_download: bool,
        cache: "DirectoryCache",
        logger: logging.Logger,
    ) -> bool:
        """Check if the file exists and log the status."""
        file_path = Path(file_path)
        target_stem = file_path.stem

        # Cache of file stems
        existing_stems = cache.get_stems(file_path.parent)

        if target_stem in existing_stems:
            if not force_download:
                logger.info("File already exists (ignoring extension): '%s'", target_stem)
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
            logger.error("Input file %s does not exist.", input_path)
            sys.exit(1)
        else:
            logger.info("Input file %s exists and is accessible.", input_path)


class DirectoryCache:
    def __init__(self, max_cache_size: int = 10) -> None:
        self._cache: OrderedDict[Path, set[str]] = OrderedDict()
        self._max_cache_size = max_cache_size

    def get_stems(self, directory: Path) -> set[str]:
        if directory in self._cache:
            self._cache.move_to_end(directory)
            return self._cache[directory]

        try:
            stems = {
                os.path.splitext(entry.name)[0]
                for entry in os.scandir(directory)
                if entry.is_file()
            }
        except FileNotFoundError:
            logger.info("Directory not yet make: %s", directory)
            stems = set()
        except PermissionError:
            logger.error("Permission denied for directory: %s", directory)
            stems = set()

        self._cache[directory] = stems
        if len(self._cache) > self._max_cache_size:
            self._cache.popitem(last=False)

        return stems

    def add_stem(self, directory: Path, stem: str) -> None:
        if directory in self._cache:
            self._cache[directory].add(stem)
            self._cache.move_to_end(directory)
        else:
            self._cache[directory] = {stem}
            if len(self._cache) > self._max_cache_size:
                self._cache.popitem(last=False)


class DownloadStatus(Enum):
    OK = 10
    VIP = 20
    FAIL = 30

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, DownloadStatus):
            return self.value < other.value
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        if isinstance(other, DownloadStatus):
            return self.value <= other.value
        return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, DownloadStatus):
            return self.value > other.value
        return NotImplemented

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, DownloadStatus):
            return self.value >= other.value
        return NotImplemented

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, DownloadStatus):
            return self.value == other.value
        return NotImplemented

    def __ne__(self, other: Any) -> bool:
        if isinstance(other, DownloadStatus):
            return self.value != other.value
        return NotImplemented


@dataclass(frozen=True)
class DownloadLogKeys:
    status: str = "status"
    dest: str = "dest"
    expect_num: str = "expect_num"
    real_num: str = "real_num"


class AlbumTracker:
    """Download log in units of albums."""

    def __init__(self, download_log: str):
        self.album_log_path = download_log
        self.download_status: dict[str, dict[str, Any]] = {}
        self.keys = DownloadLogKeys()

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

    def update_download_log(self, album_url: str, metadata: dict[str, Any]) -> None:
        album_url = LinkParser.remove_query_params(album_url)
        if album_url not in self.download_status:
            self.download_status[album_url] = {
                self.keys.status: DownloadStatus.OK,
                self.keys.dest: "",
                self.keys.expect_num: 0,
                self.keys.real_num: 0,
            }

        for key, value in metadata.items():
            if key in self.keys.__dict__.values():
                self.download_status[album_url][key] = value

    def init_download_log(self, album_url: str, **kwargs: Any) -> None:
        album_url = LinkParser.remove_query_params(album_url)
        default_metadata = {
            self.keys.status: DownloadStatus.OK,
            self.keys.dest: "",
            self.keys.expect_num: 0,
            self.keys.real_num: 0,
        }
        default_metadata.update(kwargs)
        self.download_status[album_url] = default_metadata

    @property
    def get_download_status(self) -> dict[str, dict[str, Any]]:
        return self.download_status
