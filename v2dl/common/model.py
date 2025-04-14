from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from logging import Logger

    from ..utils import BaseTaskService

PathType = str | Path
AnyDict = dict[str, Any]


@dataclass
class StaticConfig:
    bot_type: str
    custom_user_agent: str
    language: str
    chrome_args: str
    no_metadata: bool
    force_download: bool
    dry_run: bool
    terminate: bool
    use_default_chrome_profile: bool
    log_level: int
    min_scroll_distance: int
    max_scroll_distance: int
    min_scroll_step: int
    max_scroll_step: int
    max_worker: int
    rate_limit: int
    page_range: str | None

    # path relative configurations
    cookies_path: str
    download_dir: str
    metadata_path: str
    download_log_path: str
    system_log_path: str
    chrome_exec_path: str
    chrome_profile_path: str


@dataclass
class RuntimeConfig:
    url: str
    url_file: str
    download_service: "BaseTaskService"
    download_function: Callable[..., Any]
    logger: "Logger"

    def update_service(self, service: "BaseTaskService", function: Callable[..., Any]) -> None:
        """Update the download service and function dynamically."""
        self.download_service = service
        self.download_function = function


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
    encryption_config: EncryptionConfig
    _runtime_config: RuntimeConfig = field(default=None, init=True)  # type: ignore

    def bind_runtime_config(self, runtime_config: RuntimeConfig) -> None:
        self._runtime_config = runtime_config

    @property
    def runtime_config(self) -> RuntimeConfig:
        if self._runtime_config is None:
            raise ValueError("RuntimeConfig has not been bound")
        return self._runtime_config
