import importlib

from v2dl.web_bot.cookies import load_cookies
from v2dl.web_bot.drission_bot import DrissionBot
from v2dl.web_bot.get import get_bot

__all__ = ["DrissionBot", "get_bot", "load_cookies"]


def __getattr__(name: str) -> None:
    if name == "SeleniumBot":
        try:
            selenium_module = importlib.import_module(f"{__name__}.selenium_bot")
            return selenium_module.SeleniumBot
        except ModuleNotFoundError as e:
            raise ImportError(
                "Selenium is not installed. Please install it to use SeleniumBot."
            ) from e
    raise AttributeError(f"module {__name__} has no attribute {name}")
