<div align="center">

![Python >= 3.10](https://img.shields.io/badge/python->=3.10-red.svg?style=for-the-badge)
![PyPI - Version](https://img.shields.io/pypi/v/v2dl?style=for-the-badge)
![Pepy Total Downloads](https://img.shields.io/pepy/dt/v2dl?style=for-the-badge&color=027ec7)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/ZhenShuo2021/V2PH-Downloader?style=for-the-badge)  
[![Test Status](https://img.shields.io/github/actions/workflow/status/ZhenShuo2021/V2PH-Downloader/python-publish.yml?label=Tests&style=for-the-badge)](https://github.com/yt-dlp/yt-dlp/actions)
![Build Status](https://img.shields.io/github/actions/workflow/status/ZhenShuo2021/V2PH-Downloader/tests.yml?label=Build&style=for-the-badge)
![GitHub last commit](https://img.shields.io/github/last-commit/ZhenShuo2021/V2PH-Downloader?labelColor=555555&style=for-the-badge&color=027ec7)

</div>

[English](https://github.com/ZhenShuo2021/V2PH-Downloader/blob/main/README.en.md)

# V2PH Downloader
微圖坊下載器


## 特色
📦 開箱即用：不用下載額外依賴   
🌐 跨平台：全平台支援    
🔄 雙引擎：支援 DrissionPage 和 Selenium 兩種自動化選項   
🛠️ 方便：支援多帳號自動登入自動切換，支援 cookies/帳號密碼登入兩種方式   
⚡️ 快速：採用非同步事件迴圈的高效下載    
🧩 自訂：提供多種自定義參數選項   
🔑 安全：使用 PyNaCL 作為加密後端   


## 安裝
基本需求為

1. 電腦已安裝 Chrome 瀏覽器
2. Python 版本 > 3.10
3. 使用指令安裝套件

```sh
pip install v2dl
```

## 使用方式
首次執行時需要登入 V2PH 的帳號，有兩種方式

1. 帳號管理介面
使用 `v2dl -a` 進入帳號管理介面。
```sh
v2dl -a
```

2. 手動登入
帳號登入頁面的機器人偵測比較嚴格，可以隨機下載一個相簿啟動程式，遇到登入頁面程式報錯後手動登入。


### 嘗試第一次下載
v2dl 支援多種下載方式，可以下載單一相簿，也可以下載相簿列表，也支援從相簿中間開始下載，以及讀取文字文件中的所有頁面。

```sh
# 下載單一相簿
v2dl "https://www.v2ph.com/album/Weekly-Young-Jump-2015-No15"

# 下載相簿列表的所有相簿
v2dl "https://www.v2ph.com/category/nogizaka46"

# 下載文字檔中的所有頁面
v2dl -i "/path/to/urls.txt"
```

## 設定
會尋找系統設定目錄中是否存在 `config.yaml`，格式請參照根目錄的範例。

裡面可以修改捲動長度、捲動步長與速率限制等設定：

- download_dir: 設定下載位置，預設系統下載資料夾。
- download_log: 紀錄已下載的 album 頁面網址，重複的會跳過，該文件預設位於系統設定目錄。
- system_log: 設定程式執行日誌的位置，該文件預設位於系統設定目錄。
- rate_limit: 下載速度限制，預設 400 夠用也不會被封鎖。
- chrome/exec_path: 系統的 Chrome 程式位置。

系統設定目錄位置：
- Windows: `C:\Users\xxx\AppData\v2dl`
- Linux, macOS: `/Users/xxx/.config/v2dl`

### Cookies
Cookies 登入比帳號密碼更容易成功。

使用方式是用擴充套件（如 [Cookie-Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)）導出 cookies，建議選擇 Netscape 格式，並且在帳號管理工具中輸入導出的 cookie 文件位置。

> [!NOTE]   
> 導出的 Cookies 必須包含 frontend-rmt/frontend-rmu 項目。

> [!NOTE]   
> Cookies 為機密資訊，請選擇選擇[下載數量高](https://news.cnyes.com/news/id/5584471)的擴充功能套件，並且導出完成後建議將套件移除或限制存取。   

### 參數
- url: 下載目標的網址。
- -i: 下載目標的 URL 列表文字文件，每行一個 URL。
- -a: 進入帳號管理工具。
- -d: 設定下載根目錄，在分類檔案時特別有用。
- -D: 設定檔案實際下載位置。
- --no-skip: 強制下載不跳過。
- --bot: 選擇自動化工具，drission 比較不會被機器人檢測封鎖。
- --dry-run: 僅進行模擬下載，不會實際下載檔案。
- --chrome-args: 複寫啟動 Chrome 的參數，用於被機器人偵測封鎖時。
- --user-agent: 複寫 user-agent，用於被機器人偵測封鎖時。
- --terminate: 程式結束後是否關閉 Chrome 視窗。
- -q: 安靜模式。
- -v: 偵錯模式。

## 安全性簡介

> 作為好玩的套件，所以會放一些看起來沒用的功能，例如這個安全架構。其實我也只是把文檔看過一遍就拿來用，這個段落都是邊寫邊查（不過有特別選輕量套件，這個才 4MB，常見的 cryptography 25MB）。

密碼儲存使用基於現代密碼學 Networking and Cryptography (NaCl) 的加密套件 PyNaCL，系統採用三層金鑰架構完成縱深防禦：

- 第一層使用作業系統的安全亂數源 os.urandom 生成 32 位元的 encryption_key 和 salt 用以衍生金鑰，衍生金鑰函式 (KDF) 採用最先進的 argon2id 演算法，此演算法結合最先進的 Argon2i 和 Argon2d，能有效防禦 side-channel resistant 和對抗 GPU 暴力破解。

- 中間層使用主金鑰保護非對稱金鑰對，使用 XSalsa20-Poly1305 演算法加上 24-byte nonce 防禦密碼碰撞，XSalsa20 [擴展](https://meebox.io/docs/guide/encryption.html)了 Salsa20，在原本高效、不需要硬體加速的優勢上更進一步強化安全性。Poly1305 確保密碼完整性，防止傳輸過程中被篡改的問題。

- 最外層以 SealBox 實現加密，採用業界標準 Curve25519 演算法提供完美前向保密，Curve25519 只需更短的金鑰就可達到和 RSA 同等的安全強度。

最後將金鑰儲存在設有安全權限管理的資料夾，並將加密材料分開儲存於獨立的 .env 檔案中。

## 在腳本中使用

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

## 補充
1. 換頁或者下載速度太快都可能觸發封鎖，目前的設定已經均衡下載速度和避免封鎖了。
2. 會不會被封鎖也有一部分取決於網路環境，不要開 VPN 下載比較安全。
3. 謹慎使用，不要又把網站搞到關掉了，難得有資源收錄完整的。
