import sys
from collections.abc import Callable
from typing import Any

if sys.version_info < (3, 10):
    raise ImportError(
        "You are using an unsupported version of Python. Only Python versions 3.10 and above are supported by v2dl",
    )

import sys
import logging
from argparse import Namespace as NamespaceT

from . import cli, common, config, core, utils, version, web_bot

__all__ = ["cli", "common", "core", "utils", "version", "version", "web_bot"]


def create_download_service(
    args: NamespaceT,
    max_worker: int,
    rate_limit: int,
    logger: logging.Logger,
    service_type: utils.ServiceType = utils.ServiceType.ASYNC,
) -> tuple[utils.BaseTaskService, Callable[..., Any]]:
    """Create runtime configuration with integrated download service and function."""

    download_service = utils.TaskServiceFactory.create(
        service_type=service_type,
        logger=logger,
        max_workers=max_worker,
    )

    download_api = utils.DownloadAPIFactory.create(
        service_type=service_type,
        headers=common.const.HEADERS,
        rate_limit=rate_limit,
        force_download=args.force_download,
        logger=logger,
    )

    download_function = (
        download_api.download_async
        if service_type == utils.ServiceType.ASYNC
        else download_api.download
    )
    return download_service, download_function


def main() -> int:
    args = cli.parse_arguments()
    if args.version:
        print(version.__version__)  # noqa: T201
        sys.exit(0)

    if args.bot_type == "selenium":
        utils.check_module_installed()

    config_manager = config.ConfigManager()
    config_manager.load_all({"args": args})

    # setup logger
    logger = common.setup_logging(
        config_manager.get("runtime_config", "log_level"),
        log_path=config_manager.get("path", "system_log"),
        logger_name=version.__package_name__,
    )

    # suppress httpx INFO level log
    level = logging.DEBUG if args.log_level == logging.DEBUG else logging.WARNING
    logging.getLogger("httpx").setLevel(level)
    logging.getLogger("httpcore").setLevel(level)

    # prepare runtime_config
    download_service, download_function = create_download_service(
        args,
        config_manager.get("static_config", "max_worker"),
        config_manager.get("static_config", "rate_limit"),
        logger,
        utils.ServiceType.ASYNC,
    )

    # setup runtime_config
    config_manager.set("runtime_config", "url", args.url)
    config_manager.set("runtime_config", "download_service", download_service)
    config_manager.set("runtime_config", "download_function", download_function)
    config_manager.set("runtime_config", "logger", logger)
    config_manager.set("runtime_config", "user_agent", common.const.SELENIUM_AGENT)

    config_instance = config_manager.initialize_config()

    web_bot_instance = web_bot.get_bot(config_instance)
    scraper = core.ScrapeManager(config_instance, web_bot_instance)
    scraper.start_scraping()
    if not args.no_history:
        scraper.final_process()
    scraper.log_final_status()

    return 0
