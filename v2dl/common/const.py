import platform
from typing import Any

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
DEFAULT_CHROME_VERSION = "135.0.0.0"
DEFAULT_USER_AGENT = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{DEFAULT_CHROME_VERSION} Safari/537.36"


# For requests to download from the v2ph cdn, somehow the fake_useragent is not working.
HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ja;q=0.9,en-US,en;q=0.8",
    "Referer": "https://www.v2ph.com/",
}


# ============== Default User Preference ==============
# The order should be same as model.py
DEFAULT_CONFIG: dict[str, dict[str, Any]] = {
    "static_config": {
        "bot_type": "drissionpage",
        "custom_user_agent": "",
        "language": "ja",
        "chrome_args": None,
        "no_metadata": False,
        "force_download": False,
        "dry_run": False,
        "terminate": False,
        "use_default_chrome_profile": False,
        "log_level": -1,
        "min_scroll_distance": 1000,
        "max_scroll_distance": 2000,
        "min_scroll_step": 300,
        "max_scroll_step": 500,
        "max_worker": 5,
        "rate_limit": 400,
        "page_range": "",
        # path relative configurations
        "cookies_path": "",
        "download_dir": "",
        "metadata_path": "",
        "download_log_path": "",
        "system_log_path": "",
        # Do NOT pass default user-agent to config, it corrupts drissionpage's fingerprint
        "chrome_exec_path": {
            "Linux": "/usr/bin/google-chrome",
            "Darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "Windows": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        },
        "chrome_profile_path": "",
    },
    "runtime_config": {
        "url": "",
        "url_file": "",
        "bot_type": "drissionpage",
    },
    "encryption_config": {
        "key_bytes": 32,
        "salt_bytes": 16,
        "nonce_bytes": 24,
        "kdf_ops_limit": 2**4,
        "kdf_mem_limit": 2**13,
    },
}
