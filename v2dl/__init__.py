import sys

if sys.version_info < (3, 10):
    raise ImportError(
        "You are using an unsupported version of Python. Only Python versions 3.10 and above are supported by v2dl",
    )


from . import cli, common, config, core, utils, version, web_bot

__all__ = ["cli", "common", "config", "core", "utils", "version", "version", "web_bot"]
