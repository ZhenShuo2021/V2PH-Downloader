import sys

if sys.version_info < (3, 10):
    raise ImportError(
        "You are using an unsupported version of Python. Only Python versions 3.10 and above are supported by v2dl",
    )

import sys
import logging
from argparse import Namespace as NamespaceT

from . import cli, common, core, utils, version, web_bot

__all__ = ["cli", "common", "core", "utils", "version", "version", "web_bot"]


def process_input(args: NamespaceT) -> common._types.BaseConfig:
    if args.version:
        print(version.__version__)  # noqa
        sys.exit(0)

    if args.input_file:
        utils.DownloadPathTool.check_input_file(args.input_file)

    base_config = common.BaseConfigManager(common.DEFAULT_CONFIG).load()

    if args.account:
        cli.cli(base_config.encryption)

    # update base_config
    if args.min_scroll is not None:
        base_config.download.min_scroll_length = args.min_scroll
    if args.max_scroll is not None:
        base_config.download.max_scroll_length = args.max_scroll
    if args.destination is not None:
        base_config.download.download_dir = args.destination

    # suppress httpx INFO level log
    level = logging.DEBUG if args.log_level == logging.DEBUG else logging.WARNING
    logging.getLogger("httpx").setLevel(level)
    logging.getLogger("httpcore").setLevel(level)
    return base_config


def create_runtime_config(
    args: NamespaceT,
    base_config: common.BaseConfig,
    logger: logging.Logger,
    log_level: int,
    service_type: utils.ServiceType = utils.ServiceType.ASYNC,
) -> common.RuntimeConfig:
    """Create runtime configuration with integrated download service and function."""

    download_service = utils.TaskServiceFactory.create(
        service_type=service_type,
        logger=logger,
        max_workers=args.concurrency,
    )

    download_api = utils.DownloadAPIFactory.create(
        service_type=service_type,
        headers=common.const.HEADERS,
        rate_limit=base_config.download.rate_limit,
        force_download=args.force,
        logger=logger,
    )

    download_function = (
        download_api.download_async
        if service_type == utils.ServiceType.ASYNC
        else download_api.download
    )
    logger.debug("using download function name: %s", download_function.__name__)

    dest = base_config.download.download_dir
    if args.directory is not None:
        dest = args.directory
        exact_dir = True
    else:
        exact_dir = False

    return common.RuntimeConfig(
        url=args.url,
        input_file=args.input_file,
        bot_type=args.bot_type,
        chrome_args=args.chrome_args,
        user_agent=args.user_agent,
        use_chrome_default_profile=args.use_default_chrome_profile,
        terminate=args.terminate,
        history_file=args.history_file,
        no_history=args.no_history,
        download_service=download_service,
        download_function=download_function,
        dry_run=args.dry_run,
        logger=logger,
        log_level=log_level,
        force_download=args.force,
        exact_dir=exact_dir,
        download_dir=dest,
        language=args.language,
    )


def main() -> int:
    args = cli.parse_arguments()
    base_config = process_input(args)

    logger = common.setup_logging(
        args.log_level,
        log_path=base_config.paths.system_log,
        logger_name=version.__package_name__,
    )
    runtime_config = create_runtime_config(args, base_config, logger, args.log_level)

    web_bot_ = web_bot.get_bot(runtime_config, base_config)
    scraper = core.ScrapeManager(runtime_config, base_config, web_bot_)
    scraper.start_scraping()
    if not args.no_history:
        scraper.final_process()
    scraper.log_final_status()

    return 0
