import sys

from .version import __package_name__, __version__  # noqa: F401

if sys.version_info < (3, 10):
    raise ImportError(
        "You are using an unsupported version of Python. Only Python versions 3.10 and above are supported by v2dl",
    )
import atexit
import asyncio
from argparse import Namespace
from typing import Any

from v2dl import cli, common, scraper, security, version, web_bot

__all__ = ["cli", "common", "scraper", "security", "version", "web_bot"]


class V2DLApp:
    def __init__(
        self,
        default_config: dict[str, dict[str, Any]] = common.const.DEFAULT_CONFIG,
    ) -> None:
        self.default_config = default_config
        self.registered_bot: dict[str, Any] = {}

    async def run(self, args: Namespace | dict[Any, Any] | list[Any] | None = None) -> int:
        """The interface to run the full V2DL

        Args:
            args (Namespace | dict[Any, Any] | list[Any] | None, optional): The command line
            input for setup method. Defaults to None.

        Returns:
            int: The runtime status
        """
        self.scraper: scraper.ScrapeManager
        try:
            args = self.parse_arguments_wrapper(args)
            await self.init(args)
            atexit.register(self.scraper.write_metadata)  # ensure write metadata
            state = await self.scraper.start_scraping()
            msg = "Successfully bypass Cloudflare" if state else "Blocked by Cloudflare"
            self.logger.debug(f"Scraping state: {msg}")
            if state:
                self.scraper.log_final_status()
            else:
                atexit.unregister(self.scraper.write_metadata)

            return 0

        except Exception as e:
            raise RuntimeError(f"Unexpected error {e}") from e

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
            default_args = vars(cli.parse_arguments())
            return Namespace(**{key: args.get(key) for key in default_args})

        # default cli usage
        if args is None:
            return cli.parse_arguments()
        # custom input
        elif isinstance(args, Namespace):
            return args
        elif isinstance(args, dict):
            return init_attr(args)
        elif isinstance(args, list):
            return cli.parse_arguments(args)
        # unsupported input
        else:
            raise ValueError(f"Unsupported CLI args input type: {type(args)}")

    async def init(self, args: Namespace) -> None:
        """Initialize the application with the provided command-line arguments.

        The initialization process follows these steps:

        1. Initialize the ConfigManager instance.
        2. Load the default dictionary and the user-provided config.yaml.
        3. Validate CLI input for potential early return and account manager.
        4. Initialize the complete configuration:
            a. Load arguments for StaticConfig.
            b. Initialize RuntimeConfig.
            c. Merge all configuration instances to create a Config instance.
        5. Instantiate the web bot.
        6. Instantiate the ScraperManager.

        Args:
            args (Namespace): Command-line arguments. Can be replaced with a custom
                Namespace object. See cli/option.py for required fields.
        """
        self.config_manager = common.ConfigManager(self.default_config)
        self.config_manager.initialize()
        await self._check_cli_inputs(args)
        self._initialize_config(args)

        self.bot = self.get_bot(self.config)
        self.scraper = scraper.ScrapeManager(self.config, self.bot)

    async def _check_cli_inputs(self, args: Namespace) -> None:
        """Check command line inputs for quick return"""
        if args.version:
            print(version.__version__)  # noqa: T201
            sys.exit(0)

        if args.account:
            await cli.cli(self.config_manager.create_encryption_config())
            sys.exit(0)

        if args.bot_type == "selenium":
            common.utils.check_module_installed()

    def _initialize_config(self, args: Namespace) -> None:
        """Setup the options from cli.

        The order should be same as common/model.py as possible.
        """
        cset = self.config_manager.set
        config_dir = self.config_manager.get_system_config_dir()

        # =============== static config ===============
        section = "static_config"
        sub_dict = self.config_manager.get(section)

        if args.bot_type:
            cset(section, "bot_type", args.bot_type)

        headers = common.const.HEADERS
        if cua := args.custom_user_agent:
            cset(section, "custom_user_agent", cua)
            headers["User-Agent"] = cua if cua else headers["User-Agent"]

        if args.language:
            cset(section, "language", args.language)

        if args.chrome_args:
            cset(section, "chrome_args", args.chrome_args)

        if args.no_metadata:
            cset(section, "no_metadata", args.no_metadata)

        if args.force_download:
            cset(section, "force_download", args.force_download)

        if args.terminate:
            cset(section, "terminate", args.terminate)

        if args.use_default_chrome_profile:
            cset(section, "use_default_chrome_profile", args.use_default_chrome_profile)

        cset(section, "log_level", args.log_level)

        min_s = args.min_scroll_distance
        max_s = args.max_scroll_distance
        max_s = min_s * 2 if min_s > max_s else max_s
        cset(section, "min_scroll_distance", min_s)
        cset(section, "max_scroll_distance", max_s)
        cset(section, "max_worker", args.max_worker)
        cset(section, "rate_limit", args.rate_limit)
        cset(section, "page_range", args.page_range)

        # path relative configurations
        args.cookies_path = args.cookies_path if args.cookies_path else ""
        cset(section, "cookies_path", args.cookies_path)

        # download_dir
        if args.destination:
            cset(section, "download_dir", args.destination)
        else:
            cset(section, "download_dir", self.config_manager.get_default_download_dir())

        args.metadata_path = args.metadata_path if args.metadata_path else ""
        cset(section, "metadata_path", args.metadata_path)

        # not providing cli input
        if not sub_dict["download_log_path"]:
            path = str(config_dir / "downloaded_albums.txt")
            cset(section, "download_log_path", path)

        # not providing cli input
        if not sub_dict["system_log_path"]:
            path = str(config_dir / "v2dl.log")
            cset(section, "system_log_path", path)

        # not providing cli input
        path = self.config_manager.get_chrome_exec_path(sub_dict["chrome_exec_path"])
        cset(section, "chrome_exec_path", path)

        # not providing cli input
        if not sub_dict["chrome_profile_path"]:
            path = str(config_dir / "v2dl_chrome_profile")
            cset(section, "chrome_profile_path", path)

        # =============== runtime config ===============
        section = "runtime_config"
        sub_dict = self.config_manager.get(section)

        self.config_manager.set(section, "url", args.url)
        self.config_manager.set(section, "url_file", args.url_file)

        log_path = self.config_manager.get("static_config", "system_log_path")
        logger_name = version.__package_name__
        self.logger = common.setup_logging(args.log_level, log_path, logger_name)
        self.config_manager.set(section, "logger", self.logger)

        static_config = self.config_manager.create_static_config()
        runtime_config = self.config_manager.create_runtime_config()
        encryption_config = self.config_manager.create_encryption_config()
        self.config = common.model.Config(static_config, encryption_config, runtime_config)

    def register_bot(self, bot_name: str, bot: Any) -> None:
        """Register a custom bot

        Args:
            bot_type (str): The name of custom bot
            bot (Any): Web automation bot to be used
        """
        self.registered_bot[bot_name] = bot

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


def main(args: Namespace | dict[Any, Any] | list[Any] | None = None) -> int:
    loop = asyncio.get_event_loop()
    app = V2DLApp()
    return loop.run_until_complete(app.run(args))
