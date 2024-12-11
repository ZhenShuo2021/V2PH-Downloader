import sys

from v2dl import cli, common, config, core, utils, version, web_bot


def main() -> int:
    args = cli.parse_arguments()
    if args.version:
        print(version.__version__)  # noqa: T201
        sys.exit(0)

    if args.bot_type == "selenium":
        utils.check_module_installed()

    config_manager = config.ConfigManager()
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

    config_instance = config_manager.initialize_config()

    web_bot_instance = web_bot.get_bot(config_instance)
    scraper = core.ScrapeManager(config_instance, web_bot_instance)
    scraper.start_scraping()
    if not args.no_history:
        scraper.final_process()
    scraper.log_final_status()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
