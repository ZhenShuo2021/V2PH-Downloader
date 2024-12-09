<div align="center">

![Python >= 3.10](https://img.shields.io/badge/python->=3.10-red.svg?style=for-the-badge)
![PyPI - Version](https://img.shields.io/pypi/v/v2dl?style=for-the-badge)
![Pepy Total Downloads](https://img.shields.io/pepy/dt/v2dl?style=for-the-badge&color=027ec7)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/ZhenShuo2021/V2PH-Downloader?style=for-the-badge)  
[![Test Status](https://img.shields.io/github/actions/workflow/status/ZhenShuo2021/V2PH-Downloader/python-publish.yml?label=Tests&style=for-the-badge)](https://github.com/yt-dlp/yt-dlp/actions)
![Build Status](https://img.shields.io/github/actions/workflow/status/ZhenShuo2021/V2PH-Downloader/tests.yml?label=Build&style=for-the-badge)
![GitHub last commit](https://img.shields.io/github/last-commit/ZhenShuo2021/V2PH-Downloader?labelColor=555555&style=for-the-badge&color=027ec7)

</div>

# V2PH Downloader
V2PH Downloader

## Features
📦 Plug-and-play: No extra dependencies required   
🌐 Cross-platform: Supports all platforms   
🔄 Dual engines: Supports both DrissionPage and Selenium automation options   
🛠️ Convenient: Supports multiple accounts for auto-login and switching, supports cookies/password login   
⚡️ Fast: High-efficiency download with asynchronous event loop   
🧩 Customizable: Offers many configuration options   
🔑 Secure: Uses PyNaCL as encryption backend.    


## Installation
Requirements:
1. Chrome browser installed
2. Python version > 3.10
3. Install via pip

```sh
pip install v2dl
```

## Usage
On first run, login to V2PH with one of the two methods:

1. Account Management Interface
Use `v2dl -a` to enter the account management interface.
```sh
v2dl -a
```

2. Manual Login
Due to strict bot detection on login pages, you can trigger the login page by randomly downloading an album, then manually log in if errors occur.

### First Download Attempt
v2dl supports various download methods, including downloading a single album, a list of albums, starting from a specific album, or reading all pages from a text file.

```sh
# Download a single album
v2dl "https://www.v2ph.com/album/Weekly-Young-Jump-2015-No15"

# Download all albums in an album list
v2dl "https://www.v2ph.com/category/nogizaka46"

# Download all pages in a text file
v2dl -i "/path/to/urls.txt"
```

## Configuration
The program looks for a `config.yaml` file in the system configuration directory. Refer to the example in the root directory.

You can modify settings like scroll length, scroll step, and rate limit:
- download_dir: Set download location, defaults to system download folder.
- download_log: Tracks downloaded album URLs, skipped if duplicated; defaults to system configuration directory.
- system_log: Location for program logs; defaults to system configuration directory.
- rate_limit: Download speed limit, default is 400 (sufficient and prevents blocking).
- chrome/exec_path: Path to Chrome executable.

System configuration directory locations:
- Windows: `C:\Users\xxx\AppData\v2dl`
- Linux, macOS: `/Users/xxx/.config/v2dl`

### Cookies
Cookies login is often more successful than using username/password.

Use an extension (e.g., [Cookie-Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)) to export cookies in Netscape format, and input the exported cookie file path in the account manager tool.

> [!NOTE]   
> Exported cookies must include `frontend-rmt/frontend-rmu`.

> [!NOTE]   
> Cookies are sensitive information; use high-quality extensions and remove or restrict access after exporting.

### Parameters
- url: URL of the target to download.
- -i: URL list in a text file, one URL per line.
- -a: Enter the account management tool.
- -d: Configure the base download directory.
- -D: Configure the exact download directory.
- --no-skip: Force download without skipping.
- --bot: Select automation tool; Drission is less likely to be blocked by bots.
- --dry-run: Simulate the download without actual file download.
- --chrome-args: Override Chrome startup arguments, useful for bot-blocked scenarios.
- --user-agent: Override the user-agent, useful for bot-blocked scenarios.
- --terminate: Whether to close Chrome after the program ends.
- -q: Quiet mode.
- -v: Debug mode.

## Security Overview

> For fun, I included some seemingly unnecessary features like this security architecture. I mostly just glanced at the documentation, and this section was written while researching. I selected a lightweight 4MB package (while cryptography is 25MB).

Password storage uses PyNaCL, an encryption suite based on modern cryptography Networking and Cryptography (NaCl). The system uses a three-layer key architecture for defense in depth:

- The first layer uses the operating system's secure random source `os.urandom` to generate a 32-bit `encryption_key` and `salt` for key derivation using the advanced Argon2id algorithm, which combines Argon2i and Argon2d to defend against side-channel attacks and GPU brute-force cracking.

- The middle layer protects asymmetric key pairs with a master key using XSalsa20-Poly1305 with a 24-byte nonce to prevent password collisions. XSalsa20 enhances Salsa20 with greater security without hardware acceleration. Poly1305 ensures data integrity, preventing tampering during transmission.

- The outer layer implements encryption with SealBox, using Curve25519 for perfect forward secrecy, offering RSA-level security with shorter keys.

The keys are stored in a secure folder with access control, and encryption materials are stored separately in a `.env` file.

## Using in a Script

```py
import v2dl
import logging
from collections import namedtuple

your_custom_config = {
    "download": {
        "min_scroll_length": 500,
        "max_scroll_length": 1000,
        "min_scroll_step": 150,
        "max_scroll_step": 250,
        "rate_limit": 400,
        "download_dir": "v2dl",
    },
    "paths": {
        "download_log": "downloaded_albums.txt",
        "system_log": "v2dl.log",
    },
    "chrome": {
        "profile_path": "v2dl_chrome_profile",
        "exec_path": {
            "Linux": "/usr/bin/google-chrome",
            "Darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "Windows": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        },
    },
}

your_named_tuple = namedtuple("url", "input_file", "bot_type", ...)
args = your_named_tuple(url="http://v2ph.com/...", input_file="txt_file", bot_type="drission", ...)

# Initialize
log_level = logging.INFO
logger = v2dl.common.setup_logging(logging.INFO, log_path=app_config.paths.system_log)

app_config = v2dl.common.BaseConfigManager(your_custom_config)
runtime_config = create_runtime_config(args, app_config, logger, log_level)

# Start scraping
web_bot_ = v2dl.web_bot.get_bot(runtime_config, app_config)
scraper = v2dl.core.ScrapeManager(runtime_config, app_config, web_bot_)
scraper.start_scraping()
```

## Additional Notes
1. Rapid page switching or fast downloads may trigger blocks. Current settings balance speed and block prevention.
2. Block likelihood depends on network environment. Avoid using VPN for safer downloads.
3. Use cautiously to avoid overloading the website's resources.
