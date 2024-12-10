from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from logging import Logger

    from ..utils import BaseTaskService

PathType = str | Path


@dataclass
class StaticConfig:
    min_scroll_length: int
    max_scroll_length: int
    min_scroll_step: int
    max_scroll_step: int
    max_worker: int
    rate_limit: int
    no_history: bool
    language: str
    exact_dir: bool
    download_dir: str
    force_download: bool
    chrome_args: list[str] | None
    use_chrome_default_profile: bool
    dry_run: bool
    terminate: bool


@dataclass
class RuntimeConfig:
    url: str
    url_file: str
    bot_type: str
    download_service: "BaseTaskService"
    download_function: Callable[..., Any]
    logger: "Logger"
    log_level: int
    user_agent: str | None

    def update_service(self, service: "BaseTaskService", function: Callable[..., Any]) -> None:
        """Update the download service and function dynamically."""
        self.download_service = service
        self.download_function = function


@dataclass
class PathConfig:
    history_file: str
    download_log: str
    system_log: str
    chrome_exec_path: str
    chrome_profile_path: str


@dataclass(frozen=True)
class EncryptionConfig:
    key_bytes: int
    salt_bytes: int
    nonce_bytes: int
    kdf_ops_limit: int
    kdf_mem_limit: int


@dataclass
class Config:
    static_config: StaticConfig
    runtime_config: RuntimeConfig
    path_config: PathConfig
    encryption_config: EncryptionConfig
