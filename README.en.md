<div align="center">

![Python >= 3.10](https://img.shields.io/badge/python->=3.10-red.svg?style=for-the-badge)
[![PyPI - Version](https://img.shields.io/pypi/v/v2dl?style=for-the-badge)](https://pypi.org/project/v2dl/)
![Pepy Total Downloads](https://img.shields.io/pepy/dt/v2dl?style=for-the-badge&color=027ec7)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/ZhenShuo2021/V2PH-Downloader?style=for-the-badge)  
[![Test Status](https://img.shields.io/github/actions/workflow/status/ZhenShuo2021/V2PH-Downloader/tests.yml?label=Tests&style=for-the-badge)](https://github.com/ZhenShuo2021/V2PH-Downloader/actions)
[![Build Status](https://img.shields.io/github/actions/workflow/status/ZhenShuo2021/V2PH-Downloader/python-publish.yml?label=Build&style=for-the-badge)](https://github.com/ZhenShuo2021/V2PH-Downloader/actions)
[![GitHub last commit](https://img.shields.io/github/last-commit/ZhenShuo2021/V2PH-Downloader?labelColor=555555&style=for-the-badge&color=027ec7)](https://github.com/ZhenShuo2021/V2PH-Downloader/commits/main/)

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
🔑 Secure: Uses PyNaCL as encryption backend  

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

2. Cookies Login  

Logs in using cookies by specifying a cookies file. If the path is a directory, it will search for all `.txt` files containing "cookies" in their filename. This method adds the account to the login candidate list.  

```sh
v2dl -c /PATH/to/cookies
```

3. Manual Login  
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

### Cookies Login

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
- -c: Specify the cookies file to be used for this execution. If the provided path is a folder, it will automatically search for all .txt files containing "cookies" in their names within that folder. This is especially useful for users who prefer not to use account management.
- -d: Configure the base download directory.
- --force: Force download without skipping.
- --range: Specifies the download range, following the same usage as `--range` in gallery-dl.
- --bot: Select automation tool; Drission is less likely to be blocked by bots.
- `--chrome-args`: Override the arguments used to launch Chrome. This is useful when the browser is being blocked or detected by bots. Usage: `--chrome-args "window-size=800,600//guest"`. [List of all available arguments](https://stackoverflow.com/questions/38335671/where-can-i-find-a-list-of-all-available-chromeoption-arguments).
- --user-agent: Override the user-agent, useful for bot-blocked scenarios.
- --terminate: Whether to close Chrome after the program ends.
- -q: Quiet mode.
- -v: Debug mode.

## Configuration

The program will search for a `config.yaml` file in the system configuration directory and automatically load it. Please refer to the [example](https://github.com/ZhenShuo2021/V2PH-Downloader/blob/main/config.yaml) for the correct format. The configuration file can be located in the following directories based on your operating system:

- **Windows**: `C:\Users\xxx\AppData\Roaming\v2dl\config.yaml`
- **Linux, macOS**: `/Users/xxx/.config/v2dl/config.yaml`

In this file, you can modify settings like headers, language, scroll length, scroll step, and rate limits:

- **headers**: If blocked, you can customize headers. **Please note that changes will take effect only after restarting the program and refreshing the browser.**
- **language**: Used to set the download directory name, as website's machine translations are not as good as the original text.
- **use_default_chrome_profile**: Use your personal Chrome profile, which theoretically makes it harder to be blocked. However, the browser cannot be interacted with during the download process.
- **download_dir**: Set the download location; defaults to the system download folder.
- **download_log_path**: Logs the URLs of downloaded album pages, skipped if duplicated. The default location is the system configuration directory.
- **system_log_path**: Location for program logs. The default location is the system configuration directory.
- **rate_limit**: Download speed limit, default is 400, which is sufficient and prevents being blocked.
- **chrome/exec_path**: Path to the system's Chrome executable.
- **encryption_config**: If your computer's performance is insufficient, the default encryption configuration may require long decryption times. The example configuration sets all values to the minimum.

## FAQ

- Don't want to use a password manager

Use the `-c` flag to specify the path to your cookies. If a folder is provided, all `*cookies*.txt` files within it will be parsed. To avoid entering it every time, set the `cookies_path` in the config file, V2DL will load it automatically.

- Browser connection blocked

There are three common causes: a dirty IP, an improperly configured user agent, or anti-bot targeting the background tool DrissionPage. For the first, switch to a clean IP or disable your VPN. For the second, use `--user-agent` to match your environment ([what's my user agent](https://www.google.com/search?q=what%27s+my+user+agent)); be sure to restart the browser afterward. For the third, only the developer can resolve it.

- Download blocked

Create a `config.yaml` and set your custom headers.

- Incomplete downloads

First, check whether the number of images matches what's expected. Site counters can occasionally be wrong, and some pages may include VIP-only content. If everything looks fine, please file an issue with full logs.

- Architecture

The tool uses [DrissionPage](https://github.com/g1879/DrissionPage) to bypass Cloudflare checks and [httpx](https://github.com/projectdiscovery/httpx) for downloading. DrissionPage (in d mode) only allows setting a user agent, while httpx accepts headers—meaning the two settings don't conflict.

## Security Overview

> For fun, I included some seemingly unnecessary features like this security architecture. I mostly just glanced at the documentation, and this section was written while researching. I selected a lightweight 4MB package (while cryptography is 25MB).

Password storage uses PyNaCL, an encryption suite based on modern cryptography Networking and Cryptography (NaCl). The system uses a three-layer key architecture for defense in depth:

- The first layer uses the operating system's secure random source `os.urandom` to generate a 32-bit `encryption_key` and `salt` for key derivation using the advanced Argon2id algorithm, which combines Argon2i and Argon2d to defend against side-channel attacks and GPU brute-force cracking.

- The middle layer protects asymmetric key pairs with a master key using XSalsa20-Poly1305 with a 24-byte nonce to prevent password collisions. XSalsa20 enhances Salsa20 with greater security without hardware acceleration. Poly1305 ensures data integrity, preventing tampering during transmission.

- The outer layer implements encryption with SealBox, using Curve25519 for perfect forward secrecy, offering RSA-level security with shorter keys.

The keys are stored in a secure folder with access control, and encryption materials are stored separately in a `.env` file.

## Extend V2DL

You can also extend V2DL. An example code below demonstrates how to use custom default config and replace your own the web automation script.

```py
import asyncio
from v2dl import V2DLApp

custom_defaults = {
    "static_config": {
        "min_scroll_distance": 1000,
        "max_scroll_distance": 2000,
        # ...
    }
}


class CustomBot:
    def __init__(self, config_instance):
        self.config = config_instance

    def auto_page_scroll(self, full_url, page_sleep=0) -> str:
        # this function should return the html content for each album page
        print("Custom bot in action!")
        return """
<!doctype html>
<html>
<head>
    <title>Example Domain</title>

    <meta charset="utf-8" />
    <meta http-equiv="Content-type" content="text/html; charset=utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
</head>

<body>
<div>
    <h1>Example Domain</h1>
    <p>This domain is for use in illustrative examples in documents. You may use this
    domain in literature without prior coordination or asking for permission.</p>
    <p><a href="https://www.iana.org/domains/example">More information...</a></p>
</div>
</body>
</html>
"""

class ExtendedV2DL(V2DLApp):
    def _setup_runtime_config(self, config_manager, args):
        super()._setup_runtime_config(config_manager, args)
        config_manager.set("runtime_config", "user_agent", "my_custom_ua")
        print("Custom config in action!")


bot_name = "my awesome bot"
command_line_args = {"url": "https://www.v2ph.com/album/foo", "force_download": True}

app = ExtendedV2DL()
app.register_bot(bot_name, CustomBot)
app.set_bot(bot_name)
asyncio.run(app.run(command_line_args))
```

## Additional Notes

1. Rapid page switching or fast downloads may trigger blocks. Current settings balance speed and block prevention.
2. Block likelihood depends on network environment. Avoid using VPN for safer downloads.
3. Use cautiously to avoid overloading the website's resources.
