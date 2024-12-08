import json
from http.cookiejar import LoadError
from unittest.mock import mock_open, patch

import pytest

from v2dl.web_bot.cookies import (
    load_cookies,
    load_cookies_from_header_string,
    load_cookies_from_json,
    validate_file,
)


@pytest.fixture
def mock_json_file(tmp_path):
    file_path = tmp_path / "cookies.json"
    file_path.write_text(
        json.dumps([{"name": "key1", "value": "val1"}, {"name": "key2", "value": "val2"}])
    )
    return str(file_path)


@pytest.fixture
def mock_txt_file(tmp_path):
    file_path = tmp_path / "cookies.txt"
    file_path.write_text("key1=val1; key2=val2")
    return str(file_path)


@pytest.fixture
def invalid_file(tmp_path):
    file_path = tmp_path / "invalid.json"
    file_path.write_text("{invalid_json")
    return str(file_path)


# 合併 validate_file 測試
def test_validate_file():
    with (
        patch("os.path.exists", return_value=False),
        patch("v2dl.web_bot.cookies.logger.error") as mock_logger,
    ):
        assert not validate_file("nonexistent/path")
        mock_logger.assert_called_once_with("File not found: nonexistent/path")

    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.isfile", return_value=False),
        patch("v2dl.web_bot.cookies.logger.error") as mock_logger,
    ):
        assert not validate_file("not_a_file")
        mock_logger.assert_called_once_with("Not a valid file: not_a_file")

    with patch("os.path.exists", return_value=True), patch("os.path.isfile", return_value=True):
        assert validate_file("valid/path")


# 合併 load_cookies 測試
def test_load_cookies(mock_txt_file, mock_json_file, invalid_file, tmp_path):
    # 測試無效檔案
    with patch("v2dl.web_bot.cookies.validate_file", return_value=False):
        assert load_cookies("invalid/path") == {}

    # 測試 LoadError 的處理邏輯
    with (
        patch("v2dl.web_bot.cookies.validate_file", return_value=True),
        patch("v2dl.web_bot.cookies.load_cookies_from_netscape", side_effect=LoadError),
        patch(
            "v2dl.web_bot.cookies.load_cookies_from_header_string",
            return_value={"fallback_key": "fallback_val"},
        ) as mock_fallback,
    ):
        assert load_cookies(mock_txt_file) == {"fallback_key": "fallback_val"}
        mock_fallback.assert_called_once_with(mock_txt_file)

    # valid JSON format
    assert load_cookies(mock_json_file) == {"key1": "val1", "key2": "val2"}

    # invalid JSON format
    assert load_cookies(invalid_file) == {}

    # unsupported format
    unsupported_file = tmp_path / "unsupported.ext"
    unsupported_file.write_text("data")
    assert load_cookies(str(unsupported_file)) == {}


def test_load_cookies_parsers():
    with patch("builtins.open", mock_open(read_data='[{"name": "key1", "value": "val1"}]')):
        assert load_cookies_from_json("dummy.json") == {"key1": "val1"}

    with patch("builtins.open", mock_open(read_data=" key1=val1;  key2=val2 ")):
        assert load_cookies_from_header_string("dummy.txt") == {"key1": "val1", "key2": "val2"}
