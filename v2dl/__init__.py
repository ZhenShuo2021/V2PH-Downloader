import sys

from .version import __package_name__, __version__  # noqa: F401

if sys.version_info < (3, 10):
    raise ImportError(
        "You are using an unsupported version of Python. Only Python versions 3.10 and above are supported by v2dl",
    )

from argparse import Namespace
from typing import Any

from . import cli, common, config, core, utils, version, web_bot

__all__ = ["cli", "common", "config", "core", "utils", "version", "web_bot"]


class V2DLApp:
    def __init__(
        self,
        bot_type: str = "drissionpage",
        default_config: dict[str, dict[str, Any]] = common.const.DEFAULT_CONFIG,
    ) -> None:
        self.bot_type = bot_type
        self.bot_registered: dict[str, Any] = {}
        self.default_config = default_config

    def run(self, args: Namespace | dict[Any, Any] | None = None) -> int:
        args = self.__prepare_arguments(args)
        config_instance = self.setup(args)
        web_bot_instance = self.get_bot(config_instance)
        scraper = core.ScrapeManager(config_instance, web_bot_instance)
        scraper.start_scraping()
        if not config_instance.static_config.no_history:
            scraper.final_process()
        scraper.log_final_status()

        return 0

    def setup(self, args: Namespace) -> config.Config:
        if args.version:
            print(version.__version__)  # noqa: T201
            sys.exit(0)

        if args.bot_type == "selenium":
            utils.check_module_installed()

        config_manager = config.ConfigManager(self.default_config)
        config_manager.load_all({"args": args})

        # prepare logger
        logger = common.setup_logging(
            config_manager.get("runtime_config", "log_level"),
            log_path=config_manager.get("path", "system_log"),
            logger_name=version.__package_name__,
        )

        # prepare runtime_config
        download_service, download_function = utils.create_download_service(
            args,
            config_manager.get("static_config", "max_worker"),
            config_manager.get("static_config", "rate_limit"),
            logger,
            utils.ServiceType.ASYNC,
        )
        config_manager.set("runtime_config", "url", args.url)
        config_manager.set("runtime_config", "download_service", download_service)
        config_manager.set("runtime_config", "download_function", download_function)
        config_manager.set("runtime_config", "logger", logger)
        config_manager.set("runtime_config", "user_agent", common.const.SELENIUM_AGENT)

        return config_manager.initialize_config()

    def get_bot(self, config_instance: config.Config) -> Any:
        if self.bot_type in self.bot_registered:
            return self.bot_registered[self.bot_type](config_instance)
        return web_bot.get_bot(config_instance)

    def set_bot(self, bot: str) -> None:
        self.bot_type = bot

    def register_bot(self, bot_type: str, factory: Any) -> None:
        self.bot_registered[bot_type] = factory

    def parse_arguments(self) -> Namespace:
        return cli.parse_arguments()

    def __prepare_arguments(self, args: Namespace | dict[Any, Any] | None) -> Namespace:
        """Process CLI input for Config setup

        If input is None, it uses the argparse to parse inputs from command line. Otherwise, the
        inputs will be cast into a Namespace variable. Note these variables has the highest priority
        to the Config setup.
        """
        if isinstance(args, Namespace):
            return args
        elif isinstance(args, dict):
            return Namespace(**args)
        else:
            return self.parse_arguments()
