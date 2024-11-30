import logging
import argparse


def parse_arguments() -> argparse.Namespace:
    formatter = lambda prog: argparse.HelpFormatter(prog, max_help_position=36)
    parser = argparse.ArgumentParser(description="V2PH scraper.", formatter_class=formatter)

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("url", nargs="?", help="URL to scrape")
    input_group.add_argument(
        "-i",
        "--input-file",
        metavar="PATH",
        help="Path to txt file containing URL list to be downloaded",
    )
    input_group.add_argument("-a", "--account", action="store_true", help="Manage account")
    input_group.add_argument("--version", action="store_true", help="Show package version")

    parser.add_argument(
        "--bot",
        dest="bot_type",
        default="drission",
        type=str,
        choices=["selenium", "drission"],
        required=False,
        help="Type of bot to use (default: drission)",
    )

    parser.add_argument("--concurrency", default=5, type=int, help="maximum download concurrency")
    parser.add_argument("--min-scroll", type=int, help="minimum scroll length of web bot")
    parser.add_argument("--max-scroll", type=int, help="maximum scroll length of web bot")

    parser.add_argument(
        "--chrome-args",
        type=str,
        help="Override Chrome arguments (example: --chrome-args='--arg1//--arg2//--arg3')",
    )
    parser.add_argument(
        "--user-agent",
        type=str,
        help="Override user-agent (example: --user-agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)...')",
    )

    parser.add_argument("--dry-run", action="store_true", help="Dry run without downloading")
    parser.add_argument("--no-skip", action="store_true", help="Do not skip downloaded files")
    parser.add_argument("--terminate", action="store_true", help="Terminate chrome after scraping")
    parser.add_argument(
        "--use-default-chrome-profile",
        action="store_true",
        help="Use default chrome profile. Using default profile with an operating chrome is not valid",
    )

    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument("-q", "--quiet", action="store_true", help="Quiet mode")
    log_group.add_argument("-v", "--verbose", action="store_true", help="Verbose mode")
    log_group.add_argument(
        "--log-level",
        default=None,
        type=int,
        choices=range(1, 6),
        help="Set log level (1~5)",
    )

    args = parser.parse_args()

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

    args.chrome_args = args.chrome_args.split("//") if args.chrome_args else None
    args.log_level = log_level
    return args
