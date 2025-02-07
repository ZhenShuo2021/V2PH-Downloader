import sys

from .version import __package_name__, __version__  # noqa: F401

if sys.version_info < (3, 10):
    raise ImportError(
        "You are using an unsupported version of Python. Only Python versions 3.10 and above are supported by v2dl",
    )
import atexit
from argparse import Namespace
from typing import Any

from . import cli, common, core, utils, version, web_bot

__all__ = ["cli", "common", "core", "utils", "version", "web_bot"]


class V2DLApp:
    def __init__(
        self,
        default_config: dict[str, dict[str, Any]] = common.const.DEFAULT_CONFIG,
    ) -> None:
        self.default_config = default_config
        self.default_cli_values = {"url": None, "url_file": None, "account": False}
        self.registered_bot: dict[str, Any] = {}

    def run(self, args: Namespace | dict[Any, Any] | list[Any] | None = None) -> int:
        """The interface to run the full V2DL

        Args:
            args (Namespace | dict[Any, Any] | list[Any] | None, optional): The command line
            input for setup method. Defaults to None.

        Returns:
            int: The runtime status
        """
        try:
            args = self.parse_arguments_wrapper(args)
            self.initialize(args)
            atexit.register(self.scraper.write_metadata)  # ensure write metadata
            self.scraper.start_scraping()
            self.scraper.log_final_status()

            return 0

        except Exception as e:
            raise RuntimeError(f"Runtime error of V2DL: {e}") from e

    def initialize(self, args: Namespace) -> None:
        """Initialize the application with the provided command line arguments.

        This method sets up the configuration, initializes the bot, and prepares
        the scraper for execution.

        Args:
            args (Namespace): The variable from the command line. Can be replaced with a custom
            Namespace argument. Please see cli/option.py for the required fields.
        """
        self._check_cli_inputs(args)

        config_manager = common.ConfigManager(self.default_config)
        self.config = config_manager.initialize_config(args)
        runtime_config = self.setup_runtime_config(config_manager, args)
        self.config.bind_runtime_config(runtime_config)

        self.bot = self.get_bot(self.config)
        self.scraper = core.ScrapeManager(self.config, self.bot)

    def setup_runtime_config(
        self,
        config_manager: common.ConfigManager,
        args: Namespace,
        headers: dict[str, str] = common.const.HEADERS,
        user_agent: str = common.const.SELENIUM_AGENT,
    ) -> common.RuntimeConfig:
        """Initialize instances and assign to runtime config"""
        logger = common.setup_logging(
            config_manager.get("runtime_config", "log_level"),
            log_path=config_manager.get("static_config", "system_log_path"),
            logger_name=version.__package_name__,
        )
        config_manager.set("runtime_config", "logger", logger)
        config_manager.set("runtime_config", "url", args.url)
        config_manager.set("runtime_config", "user_agent", user_agent)

        download_service, download_function = utils.create_download_service(
            config_manager,
            headers,
            utils.ServiceType.ASYNC,
        )
        config_manager.set("runtime_config", "download_service", download_service)
        config_manager.set("runtime_config", "download_function", download_function)
        return config_manager.create_runtime_config()

    def get_bot(self, conf: common.Config) -> Any:
        """Get the web automation bot

        If the bot_name attribute is not set or not in registered_bot, it returns default bot.
        """
        # use user custom bot
        if hasattr(self, "bot_name") and self.bot_name in self.registered_bot:
            return self.registered_bot[self.bot_name](conf)

        # use default bot, configured in config
        return web_bot.get_bot(conf)

    def set_bot(self, bot_name: str) -> None:
        """Set the name of the custom bot"""
        self.bot_name = bot_name

    def register_bot(self, bot_name: str, bot: Any) -> None:
        """Register a custom bot

        Args:
            bot_type (str): The name of custom bot
            bot (Any): Web automation bot to be used
        """
        self.registered_bot[bot_name] = bot

    def parse_arguments_wrapper(
        self, args: Namespace | dict[Any, Any] | list[Any] | None
    ) -> Namespace:
        """Process CLI input for configuration setup.

        If args is
            - Namespace, it is returned as is.
            - dict, it is converted to a `Namespace` and parsed.
            - list, it is passed to the argument parser.
            - None, the default CLI interface is invoked.
        """

        def init_attr(args: dict[Any, Any]) -> Namespace:
            """Initialize attribute with value None"""
            mock_input = ["placeholder"]
            default_args = vars(cli.parse_arguments(mock_input))
            return Namespace(**{key: args.get(key) for key in default_args})

        if isinstance(args, Namespace):
            return args
        elif isinstance(args, dict):
            return init_attr(args)
        elif isinstance(args, list):
            return cli.parse_arguments(args)
        elif args is None:
            return cli.parse_arguments()
        else:
            raise ValueError(f"Unsupported CLI input type {type(args)}")

    def _check_cli_inputs(self, args: Namespace) -> None:
        """Check command line inputs for quick return"""
        if args.version:
            print(version.__version__)  # noqa: T201
            sys.exit(0)

        if args.account:
            config_manager = common.ConfigManager(self.default_config)
            config_manager.load_from_yaml()
            cli.cli(config_manager.create_encryption_config())
            sys.exit(0)

        if args.bot_type == "selenium":
            utils.check_module_installed()


def main(args: Namespace | dict[Any, Any] | list[Any] | None = None) -> int:
    app = V2DLApp()
    return app.run(args)
