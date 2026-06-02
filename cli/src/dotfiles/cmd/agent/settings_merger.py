"""Pure JSON helpers for merging and writing agent settings files.

All functions are pure (take/return dicts) except ``write_json_safely``,
which does an atomic write via a .tmp sibling file. No ``Path.home()`` here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_JsonDict = dict[str, Any]


def load_json_or(path: Path, default: _JsonDict) -> _JsonDict:
    """Read *path* as JSON and return it, or return *default* on any error."""
    try:
        if not path.exists():
            return default
        raw = json.loads(path.read_text())
        if not isinstance(raw, dict):
            return default
        return raw  # type: ignore[return-value]
    except (json.JSONDecodeError, OSError):
        return default


def merge_replace(settings: _JsonDict, key_path: list[str], value: Any) -> _JsonDict:
    """Return a copy of *settings* with ``settings[k0][k1][...] = value``.

    Creates intermediate dicts as needed. The original dict is not mutated.
    """
    if not key_path:
        return settings
    result = dict(settings)
    node = result
    for key in key_path[:-1]:
        child = node.get(key)
        if not isinstance(child, dict):
            child_dict: _JsonDict = {}
        else:
            child_dict = dict(child)  # type: ignore[arg-type]
        node[key] = child_dict
        node = child_dict
    node[key_path[-1]] = value
    return result


def write_json_safely(path: Path, data: _JsonDict) -> None:
    """Write *data* as JSON to *path* atomically (via a .tmp sibling).

    Creates parent directories as needed. On POSIX the rename is atomic;
    on Windows it overwrites the target (os.replace behaviour).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
