from collections.abc import Callable
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..utils import BaseTaskService

PathType = str | Path


@dataclass
class RuntimeConfig:
    url: str
    input_file: str
    bot_type: str
    chrome_args: list[str] | None
    user_agent: str | None
    terminate: bool
    download_service: "BaseTaskService"
    download_function: Callable[..., Any]
    dry_run: bool
    logger: Logger
    log_level: int
    history_file: str
    no_history: bool
    language: str = "ja"
    exact_dir: bool = False  # flag indicates if args.directory is used
    download_dir: str = ""
    force_download: bool = False
    use_chrome_default_profile: bool = False


@dataclass
class EncryptionConfig:
    key_bytes: int
    salt_bytes: int
    nonce_bytes: int
    kdf_ops_limit: int
    kdf_mem_limit: int


@dataclass
class DownloadConfig:
    min_scroll_length: int
    max_scroll_length: int
    min_scroll_step: int
    max_scroll_step: int
    rate_limit: int
    download_dir: str


@dataclass
class PathConfig:
    download_log: str
    system_log: str


@dataclass
class ChromeConfig:
    exec_path: str
    profile_path: str


@dataclass
class BaseConfig:
    download: DownloadConfig
    paths: PathConfig
    chrome: ChromeConfig
    encryption: EncryptionConfig
