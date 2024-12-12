import argparse

from ..common.const import DEFAULT_CONFIG


class CustomHelpFormatter(argparse.RawTextHelpFormatter):
    def __init__(self, prog) -> None:  # type: ignore
        super().__init__(prog, max_help_position=36)

    def _format_action_invocation(self, action):  # type: ignore
        if not action.option_strings:
            (metavar,) = self._metavar_formatter(action, action.dest)(1)
            return metavar
        else:
            parts = []
            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)

            # if the Optional takes a value, format is:
            #    -s ARGS, --long ARGS
            # change to
            #    -s, --long ARGS
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    # parts.append('%s %s' % (option_string, args_string))
                    parts.append(f"{option_string}")
                parts[-1] += f" {args_string}"
            return ", ".join(parts)


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="V2PH scraper.",
        formatter_class=CustomHelpFormatter,
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("url", nargs="?", help="URL to scrape")
    input_group.add_argument(
        "-i",
        "--input-file",
        metavar="PATH",
        dest="url_file",
        help="Path to file containing a list of URLs",
    )
    input_group.add_argument(
        "-a",
        "--account",
        action="store_true",
        help="Manage account",
    )

    parser.add_argument(
        "-d",
        "--destination",
        dest="destination",
        type=str,
        metavar="PATH",
        help="Base directory location for file downloads",
    )

    parser.add_argument(
        "-D",
        "--directory",
        dest="directory",
        type=str,
        metavar="PATH",
        help="Exact location for file downloads",
    )

    parser.add_argument(
        "-l",
        "--language",
        dest="language",
        metavar="LANG",
        help="Preferred language, used for naming the download directory (default: ja)",
    )

    parser.add_argument(
        "-f",
        "--force",
        dest="force_download",
        action="store_true",
        help="Force downloading, not skipping downloaded albums",
    )

    parser.add_argument(
        "-b",
        "--bot",
        dest="bot_type",
        type=str,
        choices=["selenium", "drissionpage"],
        required=False,
        help="Type of bot to use (default: drissionpage)",
    )

    parser.add_argument(
        "--no-history",
        dest="no_history",
        action="store_true",
        help="Disable writing json download metadata history",
    )

    parser.add_argument(
        "--history-file",
        dest="history_file",
        metavar="PATH",
        help="Path to json file for download metadata history",
    )

    parser.add_argument(
        "--max-worker",
        type=int,
        dest="max_worker",
        metavar="N",
        help="maximum download concurrency",
    )
    parser.add_argument(
        "--min-scroll",
        type=int,
        dest="min_scroll",
        metavar="N",
        help=f"minimum scroll length of web bot (default: {DEFAULT_CONFIG['static_config']['min_scroll_length']})",
    )
    parser.add_argument(
        "--max-scroll",
        type=int,
        dest="max_scroll",
        metavar="N",
        help=f"maximum scroll length of web bot (default: {DEFAULT_CONFIG['static_config']['max_scroll_length']})",
    )

    parser.add_argument(
        "--chrome-args",
        type=str,
        metavar="'--arg1//--arg2'",
        help="Override Chrome arguments",
    )

    parser.add_argument(
        "--user-agent",
        type=str,
        metavar="'Mozilla/5.0 (Windows NT 10.0; Win64; x64)...'",
        help="Override user-agent",
    )

    parser.add_argument("--dry-run", action="store_true", help="Dry run without downloading")
    parser.add_argument("--terminate", action="store_true", help="Terminate chrome after scraping")
    parser.add_argument(
        "--use-default-chrome-profile",
        action="store_true",
        help="Use default chrome profile. Using default profile with an operating chrome is not valid",
    )

    input_group.add_argument(
        "-V",
        "--version",
        action="store_true",
        help="Show package version",
    )

    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument("-q", "--quiet", action="store_true", help="Quiet mode")
    log_group.add_argument("-v", "--verbose", action="store_true", help="Verbose mode")
    log_group.add_argument(
        "--log-level",
        type=int,
        choices=range(1, 6),
        help="Set log level (1~5)",
    )

    return parser.parse_args(args)
