import importlib

from .cookies import load_cookies
from .drission_bot import DrissionBot
from .get import get_bot

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
