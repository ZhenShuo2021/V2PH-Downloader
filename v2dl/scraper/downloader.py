import os
import re
import sys
import asyncio
import logging
from collections import OrderedDict
from collections.abc import Callable
from mimetypes import guess_extension
from pathlib import Path
from typing import Literal, Optional

import httpx
from pathvalidate import sanitize_filename

from v2dl.common.const import VALID_EXTENSIONS
from v2dl.common.model import PathType

logger = logging.getLogger()


class Downloader:
    def __init__(
        self,
        headers: dict[str, str],
        speed_limit_kbps: int,
        force_download: bool,
        cache: "DirectoryCache",
        logger: logging.Logger,
        max_workers: int = 5,
    ):
        self.headers = headers
        self.speed_limit_kbps = speed_limit_kbps
        self.force_download = force_download
        self.cache = cache
        self.logger = logger
        self.max_workers = max_workers
        self.client_lock = asyncio.Lock()
        self._file_lock = asyncio.Lock()
        self.client: httpx.AsyncClient | None = None
        self.loop = asyncio.get_running_loop()
        self.client_error_event = asyncio.Event()
        self.client_reset_event = asyncio.Event()
        self.client_reset_event.set()
        self.active_tasks = 0
        self.active_tasks_lock = asyncio.Lock()

    async def download(self, url: str, dest: Path) -> bool:
        async with self._file_lock:
            if DownloadPathTool.is_file_exists(dest, self.force_download, self.cache, self.logger):
                return True

        async with self.active_tasks_lock:
            self.active_tasks += 1

        try:
            DownloadPathTool.mkdir(dest.parent)

            await self.client_reset_event.wait()

            await self.download_with_retry(
                url, dest, self.headers, speed_limit_kbps=self.speed_limit_kbps
            )
            self.logger.info("Downloaded: '%s'", dest)
            return True
        except Exception as e:
            self.logger.error("Error in async task '%s': %s", url, e)
            return False
        finally:
            async with self.active_tasks_lock:
                self.active_tasks -= 1
                if self.client_error_event.is_set() and self.active_tasks == 0:
                    self.logger.info("All tasks completed after client error, resetting client")
                    self.client_error_event.clear()
                    self.client_reset_event.set()

    async def download_core(
        self, url: str, dest: Path, headers: dict[str, str], speed_limit_kbps: Optional[int] = None
    ) -> Literal[True]:
        async with self.client_lock:
            if self.client_error_event.is_set():
                await self.client_reset_event.wait()

            client = await self.get_client()

        try:
            async with client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()

                dest.parent.mkdir(parents=True, exist_ok=True)

                total_bytes = 0
                start_time = self.loop.time()
                chunk_size = 8192

                with open(dest, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size):
                        f.write(chunk)

                        if speed_limit_kbps:
                            total_bytes += len(chunk)
                            expected_time = total_bytes / (speed_limit_kbps * 1024)
                            elapsed_time = abs(self.loop.time() - start_time)

                            if elapsed_time < expected_time:
                                await asyncio.sleep(expected_time - elapsed_time)

                return True
        except httpx.HTTPError as e:
            if not isinstance(e, httpx.HTTPStatusError):
                await self.mark_client_error()
            raise

    async def mark_client_error(self) -> None:
        self.logger.warning("Client error detected, marking for reset")
        self.client_error_event.set()
        self.client_reset_event.clear()
        await self.close_client()

    async def download_with_retry(
        self,
        url: str,
        dest: Path,
        headers: dict[str, str],
        speed_limit_kbps: Optional[int] = None,
        max_retries: int = 3,
    ) -> bool:
        retry_count = 0
        while retry_count < max_retries:
            try:
                return await self.download_core(url, dest, headers, speed_limit_kbps)
            except httpx.HTTPError as e:
                retry_count += 1
                self.logger.error(f"Retry {retry_count}/{max_retries} failed for {dest!s}: {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(2**retry_count)
                else:
                    return False
        return False

    def create_client(self) -> httpx.AsyncClient:
        self.logger.info("Creating new HTTP client")
        return httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            limits=httpx.Limits(
                max_keepalive_connections=self.max_workers, max_connections=self.max_workers * 2
            ),
        )

    async def close_client(self) -> None:
        async with self.client_lock:
            if self.client and not self.client.is_closed:
                self.logger.info("Closing HTTP client")
                await self.client.aclose()
                self.client = None

    async def get_client(self) -> httpx.AsyncClient:
        async with self.client_lock:
            if self.client is None or self.client.is_closed:
                self.client = self.create_client()
            try:
                await self.client.get("https://example.com", timeout=1.0)
            except httpx.HTTPError as e:
                self.logger.warning(
                    f"Error occurs while test connecting to https://example.com: {e}"
                )
                await self.close_client()
                self.client = self.create_client()
            return self.client


class DirectoryCache:
    def __init__(self, max_cache_size: int = 1024) -> None:
        self._cache: OrderedDict[Path, set[str]] = OrderedDict()
        self._max_cache_size = max_cache_size

    def get_files(self, directory: Path) -> set[str]:
        if directory in self._cache:
            self._cache.move_to_end(directory)
            return self._cache[directory]

        try:
            files = set()
            for entry in Path(directory).iterdir():
                if entry.is_file():
                    files.add(str(entry))
        except FileNotFoundError:
            logging.info(f"Directory not yet made: {directory}")
            files = set()
        except Exception as e:
            logging.error(f"Directory cache error: {directory}: {e}")
            files = set()

        self._cache[directory] = files
        if len(self._cache) > self._max_cache_size:
            self._cache.popitem(last=False)
        return files


class DownloadPathTool:
    @staticmethod
    def mkdir(folder_path: PathType) -> None:
        Path(folder_path).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def is_file_exists(
        file_path: PathType,
        force_download: bool,
        cache: DirectoryCache,
        logger: logging.Logger,
    ) -> bool:
        if force_download:
            return False
        file_path = Path(file_path)
        existing_files = cache.get_files(file_path.parent)
        if str(file_path) in existing_files:
            logger.info("File already exists (ignoring extension): '%s'", file_path)
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
    def get_image_ext(
        url: str, default_ext: str = "jpg", valid_ext: tuple[str, ...] = VALID_EXTENSIONS
    ) -> str:
        """Get the extension of a URL based on a list of valid extensions."""
        image_extensions = r"\.(" + "|".join(valid_ext) + r")(?:\?.*|#.*|$)"
        match = re.search(image_extensions, url, re.IGNORECASE)

        if match:
            ext = match.group(1).lower()
            # Normalize 'jpeg' to 'jpg'
            return "jpg" if ext == "jpeg" else ext

        logger.warning(f"Unrecognized extension of 'url', using default {default_ext}")
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
