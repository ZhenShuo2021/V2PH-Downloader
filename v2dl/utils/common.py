from enum import Enum
from pathlib import Path
from typing import Any


def count_files(dest: str | Path) -> int:
    path = Path(dest)
    if not path.is_dir():
        raise ValueError(f"The path '{dest}' is not a valid directory.")
    return len([f for f in path.iterdir() if f.is_file()])


def enum_to_string(obj: Any) -> str:
    if isinstance(obj, Enum):
        return obj.name
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
