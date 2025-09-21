import os
import re
import sys
import logging
from collections import OrderedDict
from collections.abc import Callable
from mimetypes import guess_extension
from pathlib import Path

import httpx
from pathvalidate import sanitize_filename

from v2dl.common.const import VALID_EXTENSIONS
from v2dl.common.model import PathType

logger = logging.getLogger()


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
