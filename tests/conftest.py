import logging
from unittest.mock import Mock

import pytest

from v2dl import V2DLApp
from v2dl.cli.option import parse_arguments
from v2dl.common import Config


@pytest.fixture
def real_app(real_args) -> V2DLApp:
    app = V2DLApp()
    app.init(real_args[0])
    return app


@pytest.fixture
def real_config(real_args) -> Config:
    app = V2DLApp()
    app.init(real_args[0])
    return app.config


@pytest.fixture
def real_args(tmp_path):
    """提供最低需求的命令行參數作整合測試"""
    expected_file_count = 12
    args = [
        "https://www.v2ph.com/album/Weekly-Young-Jump-2012-No29",
        "--min-scroll",
        "5000",
        "--max-scroll",
        "5001",
        "-f",
        "-d",
        str(tmp_path),
    ]
    return parse_arguments(args), expected_file_count


@pytest.fixture
def mock_logger():
    return Mock(spec=logging.Logger)
