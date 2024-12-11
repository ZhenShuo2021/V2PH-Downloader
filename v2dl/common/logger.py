import os
import logging
from typing import ClassVar

from colorama import Fore, Style, init


class CustomFormatter(logging.Formatter):
    COLORS: ClassVar[dict[int, str]] = {
        logging.DEBUG: Fore.LIGHTBLACK_EX,
        logging.INFO: Fore.WHITE,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }
    GREEN = Fore.GREEN
    RESET = Style.RESET_ALL

    def __init__(self, use_color: bool = True) -> None:
        super().__init__()
        init()
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        if self.use_color:
            color = self.COLORS.get(record.levelno, self.RESET)
            levelname = record.levelname.lower()
            return f"[{self.GREEN}{self.formatTime(record, '%H:%M:%S')}{self.RESET}][{color}{levelname}{self.RESET}] - {record.getMessage()}"
        else:
            # Convert levelname to lowercase for file logs
            levelname = record.levelname.lower()
            return f"[{self.formatTime(record, '%H:%M:%S')}][{levelname}] - {record.getMessage()}"


def setup_logging(
    level: int,
    log_path: str | None = None,
    logger_name: str | None = None,
    archive: bool = True,
) -> logging.Logger:
    """Configure logging with console and optional file handlers.

    Args:
        level (int): Logging level (e.g., logging.DEBUG).
        log_path (str): Path to the log file.
        archive (bool): If True, enables file logging.
    """
    logger = logging.getLogger(logger_name)

    # Clear existing handlers
    logging.root.handlers.clear()
    logger.handlers.clear()

    # Create formatters
    color_formatter = CustomFormatter(use_color=True)
    if archive:
        plain_formatter = CustomFormatter(use_color=False)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(color_formatter)
    logging.root.addHandler(console_handler)

    # File handler
    if archive and log_path:
        log_dir = os.path.dirname(log_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(plain_formatter)
        logging.root.addHandler(file_handler)

    # Set log level
    logging.root.setLevel(level)
    logger.setLevel(level)

    # suppress httpx INFO level log
    suppress_log(level)

    return logger


def suppress_log(level: int) -> None:
    level = logging.DEBUG if level == logging.DEBUG else logging.WARNING
    logging.getLogger("httpx").setLevel(level)
    logging.getLogger("httpcore").setLevel(level)


if __name__ == "__main__":
    # Set up logging
    setup_logging(logging.DEBUG, "test_logger.log")

    # Create a logger
    logger = logging.getLogger(__name__)

    # Log messages to test the configuration
    logger.debug("Debug message")
    logger.info("This is an info message.")
    logger.warning("Warning message")
    logger.error("This is an error message.")
    logger.critical("Critical message")
