import copy
import logging
import argparse
from unittest.mock import patch

import pytest

from v2dl.cli.option import CustomHelpFormatter, parse_arguments, setup_args


@pytest.fixture
def parser():
    """Fixture to create an ArgumentParser instance with CustomHelpFormatter"""
    return argparse.ArgumentParser(formatter_class=CustomHelpFormatter, prog="test_program")


def test_CustomHelpFormatter(parser):
    parser.add_argument("-f", "--file", type=str, help="Path to the file")
    help_message = parser.format_help()
    assert "-f, --file" in help_message
    assert "FILE" in help_message

    parser.add_argument("input", help="Input file")
    help_message = parser.format_help()
    assert "input" in help_message


# Test parse_arguments
@patch("argparse.ArgumentParser.parse_args")
def test_parse_arguments(mock_parse_args):
    # Mock the returned arguments
    mock_parse_args.return_value = argparse.Namespace(
        url="http://example.com",
        language="en",
        log_level=2,
        quiet=False,
        verbose=False,
        max_scroll=100,
        min_scroll=50,
        chrome_args=None,
        input_file=None,
        destination=None,
        directory=None,
        force=False,
        bot_type="drission",
        dry_run=False,
        terminate=False,
        use_default_chrome_profile=False,
        version=False,
    )

    args = parse_arguments()
    assert args.url == "http://example.com"
    assert args.language == "en"
    assert args.log_level == logging.INFO
    assert args.max_scroll == 100
    assert args.min_scroll == 50


# Test setup_args
def test_setup_args():
    args = argparse.Namespace(
        language="ja",
        quiet=False,
        verbose=False,
        log_level=None,
        max_scroll=100,
        min_scroll=50,
        chrome_args=None,
        input_file=None,
        url=None,
        force=False,
        bot_type="drission",
        dry_run=False,
        terminate=False,
        use_default_chrome_profile=False,
        version=False,
    )
    result = setup_args(args)
    assert result.language == "ja"

    # Test unsupported language
    args_error = copy.copy(args)
    args_error.language = "unsupported"
    with pytest.raises(ValueError):
        setup_args(args_error)

    # Test log level mapping
    args_q = copy.copy(args)
    args_q.quiet = True
    result = setup_args(args_q)
    assert result.log_level == logging.ERROR

    args_v = copy.copy(args)
    args_v.verbose = True
    result = setup_args(args_v)
    assert result.log_level == logging.DEBUG

    args_w = copy.copy(args)
    args_w.log_level = 4
    result = setup_args(args_w)
    assert result.log_level == logging.WARNING

    # Test scroll logic
    args.min_scroll = 300
    args.max_scroll = 100
    result = setup_args(args)
    assert result.max_scroll == 301  # max_scroll should be greater than min_scroll

    args.max_scroll = -1
    result = setup_args(args)
    assert result.max_scroll == 500  # max_scroll should be valid now

    # Test chrome args split
    args.chrome_args = "--headless//--disable-gpu"
    result = setup_args(args)
    assert result.chrome_args == ["--headless", "--disable-gpu"]
