import os
import json
import logging
from http.cookiejar import LoadError, MozillaCookieJar
from typing import Any

logger = logging.getLogger()


def load_cookies(file_path: str) -> dict[str, str] | dict[str, Any]:
    if not validate_file(file_path):
        return {}

    logger.debug(f"Reading cookies from '{file_path}'")

    try:
        if file_path.lower().endswith(".json"):
            return load_cookies_from_json(file_path)
        elif file_path.lower().endswith(".txt"):
            try:
                return load_cookies_from_netscape(file_path)
            except LoadError as e:
                logger.error(f"Loading netscape cookie error: {e}")
                return load_cookies_from_header_string(file_path)
        else:
            logger.error(f"Unsupported file type: {file_path}. Expected .json or .txt files")
            return {}

    except (json.JSONDecodeError, OSError, Exception) as e:
        logger.error(f"Error processing file {file_path}: {e!s}")

    return {}


def load_cookies_from_json(file_path: str) -> dict[str, str]:
    with open(file_path, encoding="utf-8") as f:
        cookies = json.load(f)
    if isinstance(cookies, list):
        return {item["name"]: item["value"] for item in cookies}
    else:
        logger.error("Invalid JSON format in file: %s", file_path)
        return {}


def load_cookies_from_netscape(file_path: str) -> dict[str, str | None]:
    cookie_jar = MozillaCookieJar(file_path)
    cookie_jar.load(ignore_discard=True, ignore_expires=True)
    return {cookie.name: cookie.value for cookie in cookie_jar}


def load_cookies_from_header_string(file_path: str) -> dict[str, str]:
    with open(file_path, encoding="utf-8") as f:
        header_string = f.readline()
    cookies = {}
    if header_string:
        header_string = header_string.replace(" ", "")
        pairs = header_string.split(";")
        for pair in pairs:
            if "=" in pair:
                key, value = pair.split("=", 1)
                cookies[key] = value
    return cookies


def validate_file(file_path: str) -> bool:
    if not file_path:
        logger.error(f"File path not exists: {file_path}")
        return False
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    if not os.path.isfile(file_path):
        logger.error(f"Not a valid file: {file_path}")
        return False
    return True
