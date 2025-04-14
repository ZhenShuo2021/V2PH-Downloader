import os
import logging
import argparse
from typing import Any

from ..common.const import DEFAULT_CONFIG


class ResolvePathAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):  # type: ignore
        setattr(namespace, self.dest, os.path.abspath(os.path.expanduser(values)))  # type: ignore


class CustomHelpFormatter(argparse.RawTextHelpFormatter):
    def __init__(self, prog: Any) -> None:
        super().__init__(prog, max_help_position=36)

    def _format_action_invocation(self, action: Any) -> str:
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
    """CLI 輸入的參數選項，接受以 list of string 形式接受輸入不需從 argv 輸入方便調用

    Example:
    ```
    args = ["https://www.v2ph.com/album/Weekly-Young-Jump-2012-No29", "-f", "-d", "path/to/dest"]
    parse_arguments(args)
    ```
    """
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
        action=ResolvePathAction,
        help="Path to file containing a list of URLs",
    )

    input_group.add_argument(
        "-a",
        "--account",
        action="store_true",
        help="Manage account",
    )

    input_group.add_argument(
        "-V",
        "--version",
        action="store_true",
        help="Show package version",
    )

    general = parser.add_argument_group("General Options")
    general.add_argument(
        "-b",
        "--bot",
        dest="bot_type",
        default="",
        type=str,
        choices=["selenium", "drissionpage"],
        required=False,
        help="Type of bot to use (default: drissionpage)",
    )

    general.add_argument(
        "-c",
        "--cookies-path",
        dest="cookies_path",
        type=str,
        metavar="PATH",
        action=ResolvePathAction,
        required=False,
        help="Specify the cookies path, can be a path to a file or a folder. All files\n"
        "matches the pattern `*cookies*.txt` will be added to candidate accounts.",
    )

    general.add_argument(
        "-d",
        "--destination",
        dest="destination",
        type=str,
        metavar="PATH",
        action=ResolvePathAction,
        help="Base directory location for file downloads",
    )

    general.add_argument(
        "-f",
        "--force",
        dest="force_download",
        action="store_true",
        help="Force downloading, not skipping downloaded albums",
    )

    general.add_argument(
        "-l",
        "--language",
        default="",
        dest="language",
        metavar="LANG",
        help=f"Preferred language, used for naming the download directory (default: {DEFAULT_CONFIG['static_config']['language']})",
    )

    general.add_argument(
        "--range",
        type=str,
        dest="page_range",
        metavar="RANGE",
        help="Range of pages to download. (e.g. '5', '8-20', or '1:24:3')",
    )

    general.add_argument(
        "--no-metadata",
        dest="no_metadata",
        action="store_true",
        help="Disable writing json download metadata",
    )

    general.add_argument(
        "--metadata-path",
        dest="metadata_path",
        metavar="PATH",
        action=ResolvePathAction,
        help="Path to json file for the download metadata",
    )

    general.add_argument(
        "--max-worker",
        type=int,
        default=DEFAULT_CONFIG["static_config"]["max_worker"],
        dest="max_worker",
        metavar="N",
        help="maximum download concurrency",
    )

    general.add_argument(
        "--rate-limit",
        type=int,
        default=DEFAULT_CONFIG["static_config"]["rate_limit"],
        dest="rate_limit",
        metavar="N",
        help="maximum download concurrency",
    )

    general.add_argument(
        "--min-scroll",
        type=int,
        default=DEFAULT_CONFIG["static_config"]["min_scroll_distance"],
        dest="min_scroll_distance",
        metavar="N",
        help=f"minimum scroll distance of web bot (default: {DEFAULT_CONFIG['static_config']['min_scroll_distance']})",
    )

    general.add_argument(
        "--max-scroll",
        type=int,
        default=DEFAULT_CONFIG["static_config"]["max_scroll_distance"],
        dest="max_scroll_distance",
        metavar="N",
        help=f"maximum scroll distance of web bot (default: {DEFAULT_CONFIG['static_config']['max_scroll_distance']})",
    )

    general.add_argument(
        "--chrome-args",
        type=str,
        default="",
        dest="chrome_args",
        metavar="'arg1//arg2=val'",
        help="Overwrite Chrome arguments",
    )

    general.add_argument(
        "--user-agent",
        type=str,
        default="",
        dest="custom_user_agent",
        metavar="'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'",
        help="Overwrite user-agent",
    )

    general.add_argument("--dry-run", action="store_true", help="Dry run without downloading")
    general.add_argument("--terminate", action="store_true", help="Terminate chrome after scraping")
    general.add_argument(
        "--use-default-chrome-profile",
        action="store_true",
        help="Use default chrome profile. Using default profile with an operating chrome is not valid",
    )

    output = parser.add_argument_group("Output Options")
    output.add_argument(
        "-q",
        "--quiet",
        dest="log_level",
        default=logging.INFO,
        action="store_const",
        const=logging.ERROR,
        help="Activate quiet mode",
    )
    output.add_argument(
        "-w",
        "--warning",
        dest="log_level",
        action="store_const",
        const=logging.WARNING,
        help="Print only warnings and errors",
    )
    output.add_argument(
        "-v",
        "--verbose",
        dest="log_level",
        action="store_const",
        const=logging.DEBUG,
        help="Print various debugging information",
    )

    return parser.parse_args(args)
