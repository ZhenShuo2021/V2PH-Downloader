<div align="center">

![Python >= 3.10](https://img.shields.io/badge/python->=3.10-red.svg?style=for-the-badge)
[![PyPI - Version](https://img.shields.io/pypi/v/v2dl?style=for-the-badge)](https://pypi.org/project/v2dl/)
![Pepy Total Downloads](https://img.shields.io/pepy/dt/v2dl?style=for-the-badge&color=027ec7)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/ZhenShuo2021/V2PH-Downloader?style=for-the-badge)  
[![Test Status](https://img.shields.io/github/actions/workflow/status/ZhenShuo2021/V2PH-Downloader/tests.yml?label=Tests&style=for-the-badge)](https://github.com/ZhenShuo2021/V2PH-Downloader/actions)
[![Build Status](https://img.shields.io/github/actions/workflow/status/ZhenShuo2021/V2PH-Downloader/python-publish.yml?label=Build&style=for-the-badge)](https://github.com/ZhenShuo2021/V2PH-Downloader/actions)
[![GitHub last commit](https://img.shields.io/github/last-commit/ZhenShuo2021/V2PH-Downloader?labelColor=555555&style=for-the-badge&color=027ec7)](https://github.com/ZhenShuo2021/V2PH-Downloader/commits/main/)

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

2. cookies 登入  
使用 cookies 登入，指定 cookies 檔案，如果路徑是資料夾則尋找所有檔名包含 "cookies" 的 .txt 檔案，此方式會把帳號加入到登入的候選帳號清單

```sh
v2dl -c /PATH/to/cookies
```

3. 手動登入  
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

### Cookies 登入

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
- -c: 指定此次執行所使用的 cookies 檔案。如果提供的路徑為資料夾，會自動搜尋該資料夾中所有檔名包含 "cookies" 的 .txt 檔案。這對不希望使用帳號管理功能的用戶特別有用。
- -d: 設定下載根目錄。
- --force: 強制下載不跳過。
- --range: 設定下載範圍，使用方式和 gallery-dl 的 `--range` 完全相同。
- --bot: 選擇自動化工具，drission 比較不會被機器人檢測封鎖。
- --chrome-args: 覆寫啟動 Chrome 的參數，用於被機器人偵測封鎖時，使用方法為 `--chrome-args "window-size=800,600//guest"，[所有參數](https://stackoverflow.com/questions/38335671/where-can-i-find-a-list-of-all-available-chromeoption-arguments)。
- --user-agent: 覆寫 user-agent，用於被機器人偵測封鎖時。
- --terminate: 程式結束後是否關閉 Chrome 視窗。
- -q: 安靜模式。
- -v: 偵錯模式。

## 設定

會尋找系統設定目錄中是否存在 `config.yaml` 並且自動載入，格式請參照[範例](https://github.com/ZhenShuo2021/V2PH-Downloader/blob/main/config.yaml)，存放位置請根據自己的系統選擇：

- Windows: `C:\Users\xxx\AppData\Roaming\v2dl\config.yaml`
- Linux, macOS: `/Users/xxx/.config/v2dl/config.yaml`

裡面可以修改 headers、語言、捲動長度、捲動步長與速率限制等設定：

- headers: 如果被封鎖可以自訂 headers，**請注意修改後要重啟程式開啟的瀏覽器才可以刷新**
- language: 用於設定下載目錄的名稱，因為我發現網站有些是機器翻譯還不如看原文
- use_default_chrome_profile: 使用你本人的 chrome 設定檔，理論上比較不容易被封鎖，但是下載期間無法操作瀏覽器
- download_dir: 設定下載位置，預設系統下載資料夾。
- download_log_path: 紀錄已下載的 album 頁面網址，重複的會跳過，該文件預設位於系統設定目錄。
- system_log_path: 設定程式執行日誌的位置，該文件預設位於系統設定目錄。
- rate_limit: 下載速度限制，預設 400 夠用也不會被封鎖。
- chrome/exec_path: 系統的 Chrome 程式位置。
- encryption_config: 如果電腦效能不夠，預設的加密配置可能會需要長時間解密，範例中的加密配置把所有數值都調整到最低了。

## FAQ

- 不想使用密碼管理器

請使用 `-c` 參數設定 cookies 路徑，如果是資料夾則會解析目錄底下所有的 `*cookies*.txt` 檔案。不想要每次都輸入可以在 `cookies_path` 設定路徑，V2DL 會自動讀取。

- 瀏覽器連線封鎖

封鎖原因主要有三個，不乾淨的 IP 環境、錯誤設定的 user agent、背景工具 DrissionPage 本身被反爬蟲針對。第一項是換一個乾淨的 IP 或者關閉 VPN；第二個問題可以使用 `--user-agent` 修改成適合自己的環境 ([what's my user agent](https://www.google.com/search?q=what%27s+my+user+agent))，修改後記得要重啟瀏覽器；第三個無能為力要開發者解決。

- 下載被封鎖

建立 `config.yaml` 設定自己的 headers。

- 沒有完整下載

先檢查圖片數量是否正確，網站顯示的低機率會錯誤，頁面裡面也有可能出現 VIP 限定的圖片。如果都沒問題請記錄完整訊息建立 issue。

- 架構說明

使用 [DrissionPage](https://github.com/g1879/DrissionPage) 繞過 Cloudflare 檢測，以 [httpx](https://github.com/projectdiscovery/httpx) 下載。DrissionPage 在 d mode 只能設定 user agent，而 httpx 只能設定 headers，因此兩個設定剛好不衝突。

## 安全性簡介

> 作為好玩的套件，所以會放一些看起來沒用的功能，例如這個安全架構。其實我也只是把文檔看過一遍就拿來用，這個段落都是邊寫邊查（不過有特別選輕量套件，這個才 4MB，常見的 cryptography 25MB）。

密碼儲存使用基於現代密碼學 Networking and Cryptography (NaCl) 的加密套件 PyNaCL，系統採用三層金鑰架構完成縱深防禦：

- 第一層使用作業系統的安全亂數源 os.urandom 生成 32 位元的 encryption_key 和 salt 用以衍生金鑰，衍生金鑰函式 (KDF) 採用最先進的 argon2id 演算法，此演算法結合最先進的 Argon2i 和 Argon2d，能有效防禦 side-channel resistant 和對抗 GPU 暴力破解。

- 中間層使用主金鑰保護非對稱金鑰對，使用 XSalsa20-Poly1305 演算法加上 24-byte nonce 防禦密碼碰撞，XSalsa20 [擴展](https://meebox.io/docs/guide/encryption.html)了 Salsa20，在原本高效、不需要硬體加速的優勢上更進一步強化安全性。Poly1305 確保密碼完整性，防止傳輸過程中被篡改的問題。

- 最外層以 SealBox 實現加密，採用業界標準 Curve25519 演算法提供完美前向保密，Curve25519 只需更短的金鑰就可達到和 RSA 同等的安全強度。

最後將金鑰儲存在設有安全權限管理的資料夾，並將加密材料分開儲存於獨立的 .env 檔案中。

## 擴展

你可以擴展 V2DL，以下是一個使用自訂預設值，並且替換網頁自動化套件的範例

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

## 補充

1. 換頁或者下載速度太快都可能觸發封鎖，目前的設定已經均衡下載速度和避免封鎖了。
2. 會不會被封鎖也有一部分取決於網路環境，不要開 VPN 下載比較安全。
3. 謹慎使用，不要又把網站搞到關掉了，難得有資源收錄完整的。

## 免責聲明

本軟體（以下簡稱「本軟體」）係依據 GNU 通用公共授權條款第 3 版（GNU General Public License v3.0，簡稱「GPLv3」）所授權，僅供合法之學術研究、教育及技術開發用途。使用者下載、安裝、執行或以其他任何方式使用本軟體，即表示已閱讀、理解並同意遵守 GPLv3 授權條款與本免責聲明。

本軟體係以「現狀」（AS IS）及「可得」（AS AVAILABLE）基礎提供，開發者不對本軟體之任何明示或默示保證負責，包含但不限於適售性、特定目的適用性、不侵權性、正確性、穩定性、資訊安全、第三方合法合約合規性、資料準確性或功能完整性等。開發者不擔保本軟體將不間斷、無錯誤、無漏洞或與任何系統相容。

使用者須自行確認其使用本軟體之行為已符合其所屬司法管轄區（包含但不限於中華民國、美國、歐盟成員國等）所有適用法律、法規、命令與政策，包括但不限於：

- 網路與通訊監控相關規定
- 電腦犯罪與未經授權存取行為
- 智慧財產權（著作權、商標、資料庫保護等）
- 隱私權與個資保護法（例如 GDPR, CCPA, 台灣個資法）
- 網站服務條款與 API 使用政策

本軟體所提供之一切功能、範例、腳本或技術描述，不構成任何形式之法律、資訊安全、商業操作或技術諮詢建議。開發者未對使用者特定之使用目的進行審查，亦不提供事前或事後之合法性背書。

使用者明確同意，自行對使用本軟體所產生之一切結果承擔全部責任，包括但不限於：平台封鎖、帳號停權、法律訴訟、第三方請求、民刑事處分、損害賠償或名譽損失。開發者不對任何因使用、誤用或無法使用本軟體所導致之直接、間接、偶發、特殊、懲罰性或衍生性損害負任何責任，無論其根據係基於合約、侵權、嚴格責任或其他法律理論，即使開發者已事先被告知此類損害之可能性。

本軟體不得用於任何違反法律、違反第三方授權、侵害他人權益，或未經網站或服務提供者合法授權之用途。開發者對於使用者違法使用或濫用本軟體所產生之一切後果，概不負責。

開發者保留隨時修改、終止或停止提供本軟體全部或部分內容之權利，亦得隨時修正本免責聲明，無須另行個別通知，且不因此對任何使用者或第三方承擔任何責任。

如本免責聲明之任何條款經司法機關裁定為無效或不可執行，不影響其他條款之效力。其餘條款應持續完全有效並具有約束力。
