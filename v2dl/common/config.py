import os
import logging
import platform
from copy import deepcopy
from dataclasses import fields
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from .const import AVAILABLE_LANGUAGES, DEFAULT_CONFIG
from .model import AnyDict, Config, EncryptionConfig, RuntimeConfig, StaticConfig

if TYPE_CHECKING:
    from argparse import Namespace


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
    def get_chrome_exec_path(config_data: AnyDict) -> str:
        current_os = platform.system()
        exec_path = config_data.get(current_os)
        if not exec_path:
            raise ValueError(f"Unsupported OS: {current_os}")
        if not isinstance(exec_path, str):
            raise TypeError(f"Expected a string for exec_path, got {type(exec_path).__name__}")
        return exec_path


class ConfigManager(ConfigPathTool):
    ARG_MAPPING = {
        # 因為 argparse 每個 attribute 存放在不同 dataclass，所以維護一個表設定映射
        # 每次新增一個 argparse 變數就在這個表新增映射對
        "url": ("runtime_config", "url"),
        "url_file": ("runtime_config", "url_file"),
        "bot_type": ("runtime_config", "bot_type"),
        "cookies_path": ("static_config", "cookies_path"),
        "destination": ("static_config", "download_dir"),
        "directory": ("static_config", "download_dir"),
        "force_download": ("static_config", "force_download"),
        "language": ("static_config", "language"),
        "page_range": ("static_config", "page_range"),
        "no_metadata": ("static_config", "no_metadata"),
        "metadata_path": ("static_config", "metadata_path"),
        "max_worker": ("static_config", "max_worker"),
        "min_scroll": ("static_config", "min_scroll_length"),
        "max_scroll": ("static_config", "max_scroll_length"),
        "chrome_args": ("static_config", "chrome_args"),
        "custom_user_agent": ("static_config", "custom_user_agent"),
        "dry_run": ("static_config", "dry_run"),
        "terminate": ("static_config", "terminate"),
        "use_default_chrome_profile": ("static_config", "use_default_chrome_profile"),
        "log_level": ("runtime_config", "log_level"),
    }

    def __init__(self, default_config: dict[str, AnyDict] = DEFAULT_CONFIG):
        self.default_config = default_config
        self.load_from_defaults(default_config)

    def initialize_config(self, args: "Namespace") -> "Config":
        self.load_from_defaults(self.default_config)
        self.load_from_yaml()
        self.load_from_args(args)
        self.validate_config()
        return Config(
            static_config=self.create_static_config(),
            encryption_config=self.create_encryption_config(),
        )

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

    def load_from_args(self, args: "Namespace") -> None:
        def validate_args(args: "Namespace") -> "Namespace":
            """Resolve conflicting arguments, such as log level settings."""
            if args.quiet:
                args.log_level = logging.ERROR
            elif args.verbose:
                args.log_level = logging.DEBUG
            elif args.log_level is not None:
                log_level_mapping = {
                    1: logging.DEBUG,
                    2: logging.INFO,
                    3: logging.WARNING,
                    4: logging.WARNING,
                    5: logging.CRITICAL,
                }
                args.log_level = log_level_mapping.get(args.log_level, logging.INFO)
            else:
                args.log_level = logging.INFO

            path = "static_config"
            # setup download dir
            self.set(path, "download_dir", self.get_default_download_dir())
            self.set(path, "exact_dir", False)
            if args.destination is not None:
                self.set(path, "download_dir", self.resolve_abs_path(args.destination))
            if args.directory is not None:
                self.set(path, "download_dir", self.resolve_abs_path(args.directory))
                self.set(path, "exact_dir", True)
            return args

        args = validate_args(args)
        specified_args = {
            k: v for k, v in vars(args).items() if k in self.ARG_MAPPING and v is not None
        }
        for arg_name, value in specified_args.items():
            config_section, config_key = self.ARG_MAPPING[arg_name]
            self.set(config_section, config_key, value)

        path = "static_config"
        # Manually setup force_download to prevent yaml config from getting covered
        if args.force_download:  # if set (store_true)
            self.set(path, "force_download", True)
        else:
            self.set(path, "force_download", False)

    def validate_config(self) -> None:
        config_dir = self.get_system_config_dir()

        # =====setup static config=====
        section = "static_config"
        sub_dict = self.config["static_config"]

        # validate language
        if sub_dict["language"] not in AVAILABLE_LANGUAGES:
            msg = f"Unsupported language: {sub_dict['language']}, must be in one of the {AVAILABLE_LANGUAGES}"
            raise ValueError(msg)

        # setup scroll distance
        max_s = sub_dict["max_scroll_length"]
        min_s = sub_dict["min_scroll_length"]
        if min_s > max_s:
            self.set(section, "min_scroll_length", max_s // 2)

        # parse chrome args
        if sub_dict["chrome_args"]:
            self.set(section, "chrome_args", sub_dict["chrome_args"])

        # setup chrome_exec_path if not specified
        if isinstance(sub_dict["chrome_exec_path"], dict):
            self.set(
                section,
                "chrome_exec_path",
                self.get_chrome_exec_path(sub_dict["chrome_exec_path"]),
            )

        # setup default path
        if not self.config[section]["download_log_path"]:
            path = str(config_dir / "downloaded_albums.txt")
            self.set(section, "download_log_path", path)

        if not self.config[section]["system_log_path"]:
            path = str(config_dir / "v2dl.log")
            self.set(section, "system_log_path", path)

        if not self.config[section]["chrome_profile_path"]:
            path = str(config_dir / "v2dl_chrome_profile")
            self.set(section, "chrome_profile_path", path)

    def create_static_config(self) -> StaticConfig:
        sub_dict = self.config["static_config"]
        valid_keys = {field.name for field in fields(StaticConfig)}
        return StaticConfig(**{k: v for k, v in sub_dict.items() if k in valid_keys})

    def create_encryption_config(self) -> EncryptionConfig:
        sub_dict = self.config["encryption_config"]
        return EncryptionConfig(**sub_dict)

    def create_runtime_config(self) -> RuntimeConfig:
        sub_dict = self.config["runtime_config"]
        return RuntimeConfig(
            url=sub_dict["url"],
            url_file=sub_dict["url_file"],
            bot_type=sub_dict["bot_type"],
            download_service=sub_dict["download_service"],
            download_function=sub_dict["download_function"],
            logger=sub_dict["logger"],
            log_level=sub_dict["log_level"],
        )

    def get(self, path: str, key: str, default: Any = None) -> Any:
        return self.config.get(path, {}).get(key, default)

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

    def __repr__(self) -> str:
        return f"ConfigManager(config={dict(self.config)})"


def apply_defaults(args: "Namespace", defaults: dict[str, dict[str, Any]]) -> None:
    """Set args with default value if it's None"""
    for _, path in defaults.items():
        for key, default_value in path.items():
            if hasattr(args, key) and getattr(args, key, None) is None:
                setattr(args, key, default_value)
