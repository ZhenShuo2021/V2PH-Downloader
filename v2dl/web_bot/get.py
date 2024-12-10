import time
import importlib
from typing import Any

from .drission_bot import DrissionBot
from ..config import Config
from ..utils import AccountManager, KeyManager


def get_bot(config: Config) -> Any:
    bot_classes = {
        "drissionpage": DrissionBot,
    }

    bot_type = config.runtime_config.bot_type
    logger = config.runtime_config.logger
    key_manager = KeyManager(logger, config.encryption_config)
    account_manager = AccountManager(logger, key_manager)

    # lazy import
    if bot_type == "selenium":
        try:
            selenium_module = importlib.import_module(f"{__package__}.selenium_bot")
            bot_classes["selenium"] = selenium_module.SeleniumBot
        except ModuleNotFoundError as e:
            raise ImportError(
                "Selenium is not installed. Please install it to use SeleniumBot."
            ) from e

    if bot_type not in bot_classes or bot_classes[bot_type] is None:
        raise ValueError(f"Unsupported automator type: {bot_type}")

    bot = bot_classes[bot_type](config, key_manager, account_manager)

    if bot.new_profile:
        init_new_profile(bot)
    return bot


def init_new_profile(bot: Any) -> None:
    websites: list[str] = [
        # "https://www.google.com",
        # "https://www.youtube.com",
        # "https://www.wikipedia.org",
    ]

    for url in websites:
        if isinstance(bot, DrissionBot):
            bot.page.get(url)
        elif hasattr(bot, "driver"):
            bot.driver.get(url)

        time.sleep(4)
