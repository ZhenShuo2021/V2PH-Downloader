import os
import logging
import argparse
import platform
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from .model import Config, EncryptionConfig, PathConfig, RuntimeConfig, StaticConfig
from ..common.const import AVAILABLE_LANGUAGES, DEFAULT_CONFIG, SELENIUM_AGENT

if TYPE_CHECKING:
    import argparse


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
        exec_path = config_data.get(current_os)
        if not exec_path:
            raise ValueError(f"Unsupported OS: {current_os}")
        if not isinstance(exec_path, str):
            raise TypeError(f"Expected a string for exec_path, got {type(exec_path).__name__}")
        return exec_path


class ConfigManager(ConfigPathTool):
    def __init__(
        self,
        default_config: dict[str, dict[str, Any]] = DEFAULT_CONFIG,
    ):
        self.default_config = default_config
        self.config = deepcopy(default_config)

    def load_from_defaults(self) -> None:
        self.config = {
            key: value.copy() if isinstance(value, dict) else value
            for key, value in self.default_config.items()
        }

    def load_from_yaml(self, yaml_path: str | None = None) -> None:
        if yaml_path is None:
            yaml_path_ = str(ConfigPathTool.get_system_config_dir() / "config.yaml")
        else:
            yaml_path_ = yaml_path

        if os.path.exists(yaml_path_):
            with open(yaml_path_, encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f)
                self._merge_config(self.config, yaml_config)

    def load_from_args(self, args: "argparse.Namespace") -> None:
        if args.language is not None and args.language not in AVAILABLE_LANGUAGES:
            raise ValueError(
                f"Unsupported language: {args.language}, must be in one of the {AVAILABLE_LANGUAGES}",
            )

        apply_defaults(args, self.default_config)
        # =====setup static config=====
        path = "static_config"

        # toggle log download history
        self.set(path, "no_history", args.no_history)

        # setup download dir
        self.set(path, "download_dir", ConfigPathTool.get_default_download_dir())
        if args.destination is not None:
            self.set(path, "download_dir", ConfigPathTool.resolve_abs_path(args.destination))
        if args.directory is not None:
            dest = args.directory
            self.set(path, "download_dir", ConfigPathTool.resolve_abs_path(dest))
            self.set(path, "exact_dir", True)

        # setup download folder language
        self.set(path, "language", args.language)

        # toggle force download
        self.set(path, "force_download", args.force_download)

        # setup scroll distance
        max_s = self.default_config["static_config"]["max_scroll_length"]
        min_s = self.default_config["static_config"]["min_scroll_length"]
        args.max_scroll = max_s if args.max_scroll is None else max(args.max_scroll, max_s)
        args.min_scroll = min_s if args.min_scroll is None else max(args.min_scroll, min_s)
        if args.min_scroll > args.max_scroll:
            args.min_scroll = args.max_scroll // 2
        self.set(path, "min_scroll_length", args.min_scroll)
        self.set(path, "max_scroll_length", args.max_scroll)

        # toggle dry run mode
        self.set(path, "dry_run", args.dry_run)

        # toggle terminate browser after scraping
        self.set(path, "terminate", args.terminate)

        # setup chrome_args
        if args.chrome_args:
            chrome_args = args.chrome_args.split("//")
            self.set(path, "chrome_args", chrome_args)

        # toggle default chrome profile
        self.set(path, "use_chrome_default_profile", args.use_default_chrome_profile)

        # =====setup runtime config=====
        path = "runtime_config"

        # setup url
        self.set(path, "url", args.url)

        # setup url_file
        self.set(path, "url_file", args.url_file)

        # setup log level
        if args.quiet:
            log_level = logging.ERROR
        elif args.verbose:
            log_level = logging.DEBUG
        elif args.log_level is not None:
            log_level_mapping = {
                1: logging.DEBUG,
                2: logging.INFO,
                3: logging.WARNING,
                4: logging.WARNING,
                5: logging.CRITICAL,
            }
            log_level = log_level_mapping.get(args.log_level, logging.INFO)
        else:
            log_level = logging.INFO
        self.set(path, "log_level", log_level)

        # setup browser automation bot_type
        self.set(path, "bot_type", args.bot_type)

        # =====setup path config=====
        path = "path_config"
        # setup history file path
        self.set(path, "history_file", args.history_file)

        # setup chrome_exec_path
        self.set(
            path,
            "chrome_exec_path",
            ConfigPathTool.get_chrome_exec_path(
                self.default_config["path_config"]["chrome_exec_path"],
            ),
        )

    def load_all(self, kwargs: Any) -> None:
        self.load_from_defaults()
        self.load_from_yaml()
        self.load_from_args(kwargs["args"])

        # update paths if they're not absolute
        system_config_dir = ConfigPathTool.get_system_config_dir()
        path = "path_config"
        key = "download_log"
        self.set(
            path,
            key,
            ConfigPathTool.resolve_abs_path(self.config[path][key], system_config_dir),
        )

        key = "system_log"
        self.set(
            path,
            key,
            ConfigPathTool.resolve_abs_path(self.config[path][key], system_config_dir),
        )

        key = "chrome_profile_path"
        self.set(
            path,
            key,
            ConfigPathTool.resolve_abs_path(self.config[path][key], system_config_dir),
        )

    def get(self, path: str, key: str, default: Any = None) -> Any:
        return self.config.get(path, {}).get(key, default)

    def set(self, path: str, key: str, value: Any) -> None:
        if path not in self.config:
            self.config[path] = {}
        self.config[path][key] = value

    def initialize_config(self) -> "Config":
        """初始化配置並返回對應的dataclass"""
        return Config(
            static_config=self.create_static_config(),
            runtime_config=self.create_runtime_config(),
            path_config=self.create_path_config(),
            encryption_config=self.create_encryption_config(),
        )

    def create_static_config(self) -> StaticConfig:
        key = "static_config"
        return StaticConfig(
            min_scroll_length=self.config[key]["min_scroll_length"],
            max_scroll_length=self.config[key]["max_scroll_length"],
            min_scroll_step=self.config[key]["min_scroll_step"],
            max_scroll_step=self.config[key]["max_scroll_step"],
            max_worker=self.config[key]["max_worker"],
            rate_limit=self.config[key]["rate_limit"],
            no_history=self.config[key]["no_history"],
            language=self.config[key].get("language", "ja"),
            exact_dir=self.config[key].get("exact_dir", False),
            download_dir=self.config[key].get("download_dir", ""),
            force_download=self.config[key].get("force_download", False),
            chrome_args=self.config[key].get("chrome_args", []),
            use_chrome_default_profile=self.config[key].get("use_chrome_default_profile", False),
            dry_run=self.config[key].get("dry_run", False),
            terminate=self.config[key].get("terminate", False),
        )

    def create_runtime_config(self) -> RuntimeConfig:
        """Create runtime config.

        Note that the download service and function is None!
        """
        key = "runtime_config"
        return RuntimeConfig(
            url=self.config[key]["url"],
            url_file=self.config[key]["url_file"],
            bot_type=self.config[key]["bot_type"],
            download_service=self.config[key]["download_service"],
            download_function=self.config[key]["download_function"],
            logger=self.config[key]["logger"],
            log_level=self.config[key].get("log_level", logging.INFO),
            user_agent=self.config[key].get("user_agent", SELENIUM_AGENT),
        )

    def create_path_config(self) -> PathConfig:
        key = "path_config"
        # return PathConfig(
        #     history_file=self.config[key]["history_file"],
        #     download_log=self.config[key]["download_log"],
        #     system_log=self.config[key]["system_log"],
        #     chrome_exec_path=self.config[key]["chrome_exec_path"],
        #     profile_path=self.config[key]["profile_path"],
        # )
        return PathConfig(**self.config[key])

    def create_encryption_config(self) -> EncryptionConfig:
        key = "encryption_config"
        return EncryptionConfig(**self.config[key])
        # return EncryptionConfig(
        #     key_bytes=self.get("key_bytes"),
        #     salt_bytes=self.get("salt_bytes"),
        #     nonce_bytes=self.get("nonce_bytes"),
        #     kdf_ops_limit=self.get("kdf_ops_limit"),
        #     kdf_mem_limit=self.get("kdf_mem_limit"),
        # )

    def _merge_config(self, base: dict[str, Any], custom: dict[str, Any]) -> dict[str, Any]:
        """Recursively merge custom config into base config."""
        for key, value in custom.items():
            if isinstance(value, dict) and key in base:
                self._merge_config(base[key], value)
            else:
                base[key] = value
        return base

    def __repr__(self) -> str:
        return f"ConfigManager(config={dict(self.config)})"


def apply_defaults(args: argparse.Namespace, defaults: dict[str, dict[str, Any]]) -> None:
    """Set args with default value if it's None"""
    for _, path in defaults.items():
        for key, default_value in path.items():
            if hasattr(args, key) and getattr(args, key, None) is None:
                setattr(args, key, default_value)
