"""TOML helpers for codex ``~/.codex/config.toml`` MCP server blocks.

Uses ``tomllib`` (stdlib, read-only) for parsing and a minimal hand-written
serialiser for the ``[mcp_servers.<name>]`` tables — the only section we write.
Values are always simple types: strings, lists of strings, and string→string dicts.

``tomli_w`` is NOT required (and not installed in this project).
"""

from __future__ import annotations

import tomllib
from typing import Any, cast

_JsonDict = dict[str, Any]
# Internal type alias that gives Pyright strict enough info to check iteration.
_ObjDict = dict[str, object]


# ---------------------------------------------------------------------------
# Minimal TOML serialiser for mcp_servers tables
# ---------------------------------------------------------------------------


def _toml_value(v: object) -> str:
    """Serialise a single TOML value (string, list[str], or dict[str,str])."""
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, str):
        escaped = v.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(v, list):
        items = ", ".join(_toml_value(item) for item in cast(list[object], v))
        return f"[{items}]"
    if isinstance(v, dict):
        d = cast(_ObjDict, v)
        pairs = ", ".join(f'"{k}" = {_toml_value(val)}' for k, val in d.items())
        return "{" + pairs + "}"
    # Fallback: ints, floats, etc.
    return str(v)


def render_mcp_toml(servers: _JsonDict) -> str:
    """Render *servers* as ``[mcp_servers.<name>]`` TOML blocks.

    Each key in *servers* becomes one table; its dict value provides the fields.
    Returns a string suitable for embedding in a TOML config file.
    """
    lines: list[str] = []
    for name, config in cast(_ObjDict, servers).items():
        lines.append(f"[mcp_servers.{name}]")
        if isinstance(config, dict):
            for k, v in cast(_ObjDict, config).items():
                lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")  # blank line between tables
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section-aware upsert
# ---------------------------------------------------------------------------


def _drop_mcp_servers_section(text: str) -> str:
    """Remove all ``[mcp_servers...]`` tables and their content from *text*."""
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    inside = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[mcp_servers"):
            inside = True
            continue
        if inside and stripped.startswith("[") and not stripped.startswith("[mcp_servers"):
            inside = False
        if not inside:
            result.append(line)
    return "".join(result)


def upsert_section(existing_toml: str, servers: _JsonDict) -> str:
    """Replace the ``mcp_servers`` section in *existing_toml* with *servers*.

    Strategy:
    1. Parse *existing_toml* with ``tomllib`` to validate it.
    2. Drop all existing ``[mcp_servers.*]`` tables from the raw text.
    3. Append the freshly rendered ``render_mcp_toml(servers)`` block.

    Raises ``tomllib.TOMLDecodeError`` if *existing_toml* is invalid TOML.
    """
    # Validate — raises on invalid TOML
    tomllib.loads(existing_toml)

    # Remove existing mcp_servers tables, preserve everything else
    cleaned = _drop_mcp_servers_section(existing_toml).rstrip("\n")

    new_block = render_mcp_toml(servers)
    if not new_block.strip():
        return cleaned + "\n" if cleaned else ""

    separator = "\n\n" if cleaned else ""
    return cleaned + separator + new_block
