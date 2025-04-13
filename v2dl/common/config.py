import os
import platform
from copy import deepcopy
from dataclasses import fields
from pathlib import Path
from typing import Any

import yaml

from v2dl.common.const import DEFAULT_CONFIG
from v2dl.common.model import AnyDict, EncryptionConfig, RuntimeConfig, StaticConfig


class ConfigPathTool:
    @staticmethod
    def resolve_abs_path(path: str | Path, base_dir: str | Path | None = None) -> Path:
        """Resolve '~', add path with base_dir if input is not absolute path."""
        base_dir = base_dir or ConfigPathTool.get_default_download_dir()
        path = Path(path).expanduser()
        return Path(base_dir) / path if not path.is_absolute() else path

    @staticmethod
    def get_system_config_dir() -> Path:
        """Return the config directory."""
        if platform.system() == "Windows":
            base = os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")
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
    def get_chrome_exec_path(dict_data: AnyDict) -> str:
        current_os = platform.system()
        exec_path = dict_data.get(current_os)
        if not exec_path:
            raise ValueError(f"Unsupported OS: {current_os}")
        if not isinstance(exec_path, str):
            raise TypeError(f"Expected a string for exec_path, got {type(exec_path).__name__}")
        return exec_path


class ConfigManager(ConfigPathTool):
    def __init__(self, default_config: dict[str, AnyDict] = DEFAULT_CONFIG):
        self.default_config = default_config

    def initialize(self) -> None:
        self.load_from_defaults(self.default_config)
        self.load_from_yaml()

    def load_from_defaults(self, default_config: AnyDict | None = None) -> None:
        """This reset config to default"""
        default_config = default_config or self.default_config
        self.config = deepcopy(default_config)

    def load_from_yaml(self, yaml_path: str | None = None) -> None:
        if yaml_path is None:
            config_file = str(self.get_system_config_dir() / "config.yaml")
        else:
            config_file = yaml_path

        if os.path.exists(config_file):
            with open(config_file, encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f)
            self._merge_config(self.config, yaml_config)

    def create_static_config(self) -> StaticConfig:
        sub_dict = self.config["static_config"]
        valid_keys = {field.name for field in fields(StaticConfig)}
        return StaticConfig(**{k: v for k, v in sub_dict.items() if k in valid_keys})

    def create_encryption_config(self) -> EncryptionConfig:
        return EncryptionConfig(**self.config["encryption_config"])

    def create_runtime_config(self) -> RuntimeConfig:
        sub_dict = self.config["runtime_config"]
        return RuntimeConfig(
            url=sub_dict["url"],
            url_file=sub_dict["url_file"],
            download_service=sub_dict["download_service"],
            download_function=sub_dict["download_function"],
            logger=sub_dict["logger"],
        )

    def get(self, path: str, key: str | None = None, default: Any = None) -> Any:
        if key is None:
            return self.config[path]
        return self.config[path].get(key, default)

    def set(self, path: str, key: str, value: Any) -> None:
        if path not in self.config:
            self.config[path] = {}
        self.config[path][key] = value

    def _merge_config(self, original: AnyDict, new: AnyDict) -> AnyDict:
        """Recursively merge new config into original config."""
        for key, value in new.items():
            if isinstance(value, dict) and key in original:
                self._merge_config(original[key], value)
            else:
                if value:
                    original[key] = value
        return original
