# ============== Default User Preference ==============
import platform
from typing import Any

DEFAULT_CONFIG: dict[str, dict[str, Any]] = {
    "static_config": {
        "min_scroll_length": 1000,
        "max_scroll_length": 2000,
        "min_scroll_step": 300,
        "max_scroll_step": 500,
        "max_worker": 5,
        "rate_limit": 400,
        "language": "ja",
        "no_history": False,
        "exact_dir": False,
        "force_download": False,
        "use_chrome_default_profile": False,
        "dry_run": False,
    },
    "runtime_config": {
        "bot_type": "drissionpage",
        "url_file": None,
    },
    "path_config": {
        "history_file": "",
        "download_log": "downloaded_albums.txt",
        "system_log": "v2dl.log",
        "chrome_profile_path": "v2dl_chrome_profile",
        "chrome_exec_path": {
            "Linux": "/usr/bin/google-chrome",
            "Darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "Windows": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        },
    },
    "encryption_config": {
        "key_bytes": 32,
        "salt_bytes": 16,
        "nonce_bytes": 24,
        "kdf_ops_limit": 2**4,
        "kdf_mem_limit": 2**13,
    },
}


# ============== System ==============
BASE_URL = "https://www.v2ph.com"
AVAILABLE_LANGUAGES = ("zh-Hans", "ja", "zh-Hant", "en", "ko", "es", "fr", "ru", "de", "ar")
VALID_EXTENSIONS = (
    "jpg",
    "jpeg",
    "JPG",
    "JPEG",
    "png",
    "PNG",
    "gif",
    "bmp",
    "webp",
    "webm",
    "tiff",
    "svg",
    "mp4",
    "mov",
    "avi",
    "mkv",
    "wmv",
    "flv",
    "m4v",
)
IMAGE_PER_PAGE = 10

# For selenium webdriver
USER_OS = platform.system()
DEFAULT_VERSION = "131.0.6778.109"
SELENIUM_AGENT = f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{DEFAULT_VERSION} Safari/537.36"


# For requests to download from the v2ph cdn, somehow the fake_useragent is not working.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.59 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.google.com/",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    # "Sec-Fetch-Dest": "document",
    # "Sec-Fetch-Mode": "navigate",
    # "Sec-Fetch-Site": "none",
    # "Sec-Fetch-User": "?1",
    # "Cache-Control": "max-age=0",
}
