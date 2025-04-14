import os
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

    每次新增選項必須修改以下幾個地方:
        1. parse_arguments 本身
        2. common/model.py 設定存放的 dataclass
        3. common/config.py 設定 dataclass 映射表
        4. common/config.py/validate 驗證參數 (如果需要)
        5. common/const.py 新增預設值 (如果可設定為 yaml 預設值)
        6. config.yaml 更新使用範例 (如果需要修改 const.py)
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

    parser.add_argument(
        "-d",
        "--destination",
        dest="destination",
        type=str,
        metavar="PATH",
        action=ResolvePathAction,
        help="Base directory location for file downloads",
    )

    parser.add_argument(
        "-D",
        "--directory",
        dest="directory",
        type=str,
        metavar="PATH",
        action=ResolvePathAction,
        help="Exact location for file downloads",
    )

    parser.add_argument(
        "-f",
        "--force",
        dest="force_download",
        action="store_true",
        help="Force downloading, not skipping downloaded albums",
    )

    parser.add_argument(
        "-l",
        "--language",
        dest="language",
        metavar="LANG",
        help="Preferred language, used for naming the download directory (default: ja)",
    )

    parser.add_argument(
        "--range",
        dest="page_range",
        metavar="RANGE",
        help="Range of pages to download. (e.g. '5', '8-20', or '1:24:3')",
    )

    parser.add_argument(
        "--no-metadata",
        dest="no_metadata",
        action="store_true",
        help="Disable writing json download metadata",
    )

    parser.add_argument(
        "--metadata-path",
        dest="metadata_path",
        metavar="PATH",
        action=ResolvePathAction,
        help="Path to json file for the download metadata",
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
        default="",
        dest="chrome_args",
        metavar="'arg1//arg2=val'",
        help="Overwrite Chrome arguments",
    )

    parser.add_argument(
        "--user-agent",
        type=str,
        default="",
        dest="custom_user_agent",
        metavar="'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'",
        help="Overwrite user-agent",
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
