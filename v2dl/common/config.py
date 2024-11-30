import os
import platform
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from ._types import BaseConfig, ChromeConfig, DownloadConfig, EncryptionConfig, PathConfig


class ConfigPathTool:
    @staticmethod
    def resolve_abs_path(path: str | Path, base_dir: str | Path) -> str | Path:
        """Resolve '~', add path with base_dir if input is not absolute path."""
        path = os.path.expanduser(path)
        return os.path.join(base_dir, path) if not os.path.isabs(path) else path

    @staticmethod
    def get_system_config_dir() -> Path:
        """Return the config directory."""
        if platform.system() == "Windows":
            base = os.getenv("APPDATA", "")
        else:
            base = os.path.expanduser("~/.config")
        return Path(base) / "v2dl"

    @staticmethod
    def get_default_download_dir() -> Path:
        return Path.home() / "Downloads"

    @staticmethod
    def get_download_dir(download_dir: str) -> str:
        sys_dl_dir = ConfigPathTool.get_default_download_dir()
        result_dir = (
            ConfigPathTool.resolve_abs_path(download_dir, sys_dl_dir)
            if download_dir
            else sys_dl_dir
        )
        result_dir = Path(result_dir)
        return str(result_dir)

    @staticmethod
    def get_chrome_exec_path(config_data: dict[str, Any]) -> str:
        current_os = platform.system()
        exec_path = config_data["chrome"]["exec_path"].get(current_os)
        if not exec_path:
            raise ValueError(f"Unsupported OS: {current_os}")
        if not isinstance(exec_path, str):
            raise TypeError(f"Expected a string for exec_path, got {type(exec_path).__name__}")
        return exec_path


class BaseConfigManager(ConfigPathTool):
    """Load and process configs based on user platform.

    The DEFAULT_CONFIG is a nested dict, after processing, the ConfigManager.load() returns a
    Config dataclass consists of DownloadConfig, PathConfig, ChromeConfig dataclasses.
    """

    def __init__(self, base_config: dict[str, dict[str, Any]], config_dir: str | None = None):
        self.base_config = base_config
        self.config_dir = config_dir

    def load(self) -> BaseConfig:
        """Load configuration from files and environment."""
        system_config_dir = BaseConfigManager.get_system_config_dir()
        if self.config_dir is not None:  # overwrite the config_dir
            system_config_dir = Path(self.config_dir)

        custom_config_path = system_config_dir / "config.yaml"
        custom_env_path = system_config_dir / ".env"

        # Load environment variables
        if custom_env_path.exists():
            load_dotenv(custom_env_path)

        # Load and merge configurations
        if custom_config_path.exists():
            with open(custom_config_path) as f:
                custom_config = yaml.safe_load(f)
                if custom_config:  # not empty
                    self.base_config = BaseConfigManager._merge_config(
                        self.base_config,
                        custom_config,
                    )

        # Check file paths
        for key, path in self.base_config["paths"].items():
            self.base_config["paths"][key] = BaseConfigManager.resolve_abs_path(
                path,
                system_config_dir,
            )

        self.base_config["chrome"]["profile_path"] = BaseConfigManager.resolve_abs_path(
            self.base_config["chrome"]["profile_path"],
            system_config_dir,
        )

        # Check download_dir path
        download_dir = self.base_config["download"].get("download_dir", "").strip()
        self.base_config["download"]["download_dir"] = BaseConfigManager.get_download_dir(
            download_dir,
        )

        return BaseConfig(
            download=DownloadConfig(**self.base_config["download"]),
            paths=PathConfig(**self.base_config["paths"]),
            chrome=ChromeConfig(
                exec_path=BaseConfigManager.get_chrome_exec_path(self.base_config),
                profile_path=self.base_config["chrome"]["profile_path"],
            ),
            encryption=EncryptionConfig(
                **self.base_config.get("encryption", self.base_config["encryption"]),
            ),
        )

    @staticmethod
    def _merge_config(base: dict[str, Any], custom: dict[str, Any]) -> dict[str, Any]:
        """Recursively merge custom config into base config."""
        for key, value in custom.items():
            if isinstance(value, dict) and key in base:
                BaseConfigManager._merge_config(base[key], value)
            else:
                base[key] = value
        return base
