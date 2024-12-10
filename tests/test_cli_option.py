import argparse
from unittest.mock import patch

import pytest

from v2dl.cli.option import CustomHelpFormatter, parse_arguments


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
        chrome_args=[],
        input_file=None,
        destination=None,
        directory=None,
        force=False,
        bot_type="drissionpage",
        dry_run=False,
        terminate=False,
        use_default_chrome_profile=False,
        version=False,
    )

    args = parse_arguments()
    assert args.url == "http://example.com"
    assert args.language == "en"
    assert args.max_scroll == 100
    assert args.min_scroll == 50
