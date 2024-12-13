import os
import time
import random
from abc import ABC, abstractmethod
from logging import Logger
from subprocess import run
from typing import Any

from ..common import const
from ..config import Config
from ..utils import AccountManager, KeyManager


class BaseBot(ABC):
    """Abstract base class for bots, defining shared behaviors."""

    def __init__(
        self,
        config: Config,
        key_manager: KeyManager,
        account_manager: AccountManager,
    ):
        self.config = config
        self.runtime_config = config.runtime_config
        self.close_browser = config.static_config.terminate
        self.logger = config.runtime_config.logger

        self.key_manager = key_manager
        self.account_manager = account_manager
        key_pair = self.key_manager.load_keys()
        self.private_key, self.public_key = key_pair.private_key, key_pair.public_key

        self.new_profile = False

    @abstractmethod
    def init_driver(self) -> Any:
        """Initialize the browser driver."""

    @abstractmethod
    def close_driver(self) -> None:
        """Close the browser and handle cleanup."""

    def prepare_chrome_profile(self) -> str:
        user_data_dir = self.config.path_config.chrome_profile_path

        if not os.path.exists(user_data_dir):
            os.makedirs(user_data_dir)
            self.new_profile = True
        else:
            self.new_profile = False

        return user_data_dir

    def auto_page_scroll(
        self,
        url: str,
        max_retry: int = 3,
        page_sleep: int = 5,
        fast_scroll: bool = True,
    ) -> str:
        """Scroll page automatically with retries and Cloudflare challenge handle.

        The main function of this class.

        Args:
            url (str): Target URL
            max_retry (int): Maximum number of retry attempts. Defaults to 3
            page_sleep (int): The sleep time after reaching page bottom
            fast_scroll (bool): Whether to use fast scroll. Might be blocked by Cloudflare

        Returns:
            str: Page HTML content or error message
        """
        raise NotImplementedError("Subclasses must implement automated retry logic.")

    def handle_login(self) -> bool:
        """Login logic, implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement login logic.")

    def human_like_type(self, element: Any, text: str) -> None:
        """Simulate human-like typing into a field."""
        raise NotImplementedError("Subclasses must implement scroll behavior.")

    def scroll_page(self) -> None:
        """Simulate human-like scrolling behavior."""
        raise NotImplementedError("Subclasses must implement scroll behavior.")


class BaseBehavior:
    pause_time = (0.1, 0.3)

    @staticmethod
    def random_sleep(min_time: float = 1.0, max_time: float = 5.0) -> None:
        time.sleep(random.uniform(min_time, max_time))


class BaseScroll:
    def __init__(self, config: Config, logger: Logger) -> None:
        self.config = config
        self.logger = logger
        self.scroll_position = 0
        self.last_content_height = 0
        self.successive_scroll_count = 0
        self.max_successive_scrolls = random.randint(5, 10)


def get_chrome_version_unix(chrome_path: str) -> str:
    try:
        result = run([chrome_path, "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split()[-1]
    except Exception:
        pass
    return const.DEFAULT_VERSION


def get_chrome_version() -> str:
    system = const.USER_OS

    if system == "Windows":
        import winreg

        try:
            reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:  # type: ignore
                chrome_path, _ = winreg.QueryValueEx(key, "")  # type: ignore

            if os.path.exists(chrome_path):
                chrome_path = chrome_path.replace("\\", "\\\\")
                file_info = os.popen(  # nosec
                    f'wmic datafile where name="{chrome_path}" get Version /value',
                ).read()
                version = [
                    line.split("=")[1] for line in file_info.splitlines() if "Version=" in line
                ]
                return version[0] if version else const.DEFAULT_VERSION
        except Exception:
            pass
        return const.DEFAULT_VERSION

    if system == "Darwin":  # macOS
        return get_chrome_version_unix(
            const.DEFAULT_CONFIG["path_config"]["chrome_exec_path"]["Darwin"]
        )

    if system == "Linux":
        return get_chrome_version_unix(
            const.DEFAULT_CONFIG["path_config"]["chrome_exec_path"]["Linux"]
        )

    return const.DEFAULT_VERSION
