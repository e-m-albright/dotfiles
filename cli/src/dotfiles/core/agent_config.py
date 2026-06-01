"""Pydantic config models for the agent-overview config files.

Each model is tolerant of extra keys (extra="ignore") so new fields in the
config files don't break parsing.  ``load_config`` is the single entry-point
for reading a config file from disk.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pydantic
from pydantic import BaseModel, ConfigDict, TypeAdapter

# ---------------------------------------------------------------------------
# Config file models
# ---------------------------------------------------------------------------


class McpServerEntry(BaseModel):
    """One entry in agents/shared/mcp-servers.json."""

    model_config = ConfigDict(extra="ignore")

    targets: list[str] = []


# TypeAdapter for the whole mcp-servers.json dict (object-valued entries only).
_MCP_SERVERS_ADAPTER: TypeAdapter[dict[str, McpServerEntry]] = TypeAdapter(
    dict[str, McpServerEntry]
)


class ClaudeHooksConfig(BaseModel):
    """claude/hooks.json and codex/hooks.json — .hooks keys are the events."""

    model_config = ConfigDict(extra="ignore")

    hooks: dict[str, object] = {}


class CursorHookEntry(BaseModel):
    """One entry in cursor hooks list."""

    model_config = ConfigDict(extra="ignore")

    event: str = ""


class CursorHooksConfig(BaseModel):
    """cursor/hooks/hooks.json — .hooks is a list of objects with an event key."""

    model_config = ConfigDict(extra="ignore")

    hooks: list[CursorHookEntry] = []


class PermissionsBlock(BaseModel):
    """Bare permissions object with allow/deny lists."""

    model_config = ConfigDict(extra="ignore")

    allow: list[object] = []
    deny: list[object] = []


class SettingsWithPermissions(BaseModel):
    """~/.claude/settings.json and cursor/cli-config.json — wrapper with a .permissions key."""

    model_config = ConfigDict(extra="ignore")

    permissions: PermissionsBlock = PermissionsBlock()


# ---------------------------------------------------------------------------
# Generic loader
# ---------------------------------------------------------------------------


def load_config[M: BaseModel](
    path: Path,
    model: type[M],
) -> M | None:
    """Read *path* and parse it as *model*.

    Returns None if the file is missing, the JSON is invalid, or pydantic
    rejects the payload.
    """
    try:
        if not path.exists():
            return None
        text = path.read_text()
        return model.model_validate_json(text)
    except (pydantic.ValidationError, ValueError):
        return None


def load_mcp_servers(path: Path) -> dict[str, McpServerEntry]:
    """Read mcp-servers.json; return only object-valued entries parsed as McpServerEntry."""
    if not path.exists():
        return {}
    try:
        raw: object = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    raw_dict = cast(dict[str, object], raw)
    # Filter to object-only entries before validation
    obj_only: dict[str, dict[str, object]] = {
        k: cast(dict[str, object], v) for k, v in raw_dict.items() if isinstance(v, dict)
    }
    try:
        return _MCP_SERVERS_ADAPTER.validate_python(obj_only)
    except pydantic.ValidationError:
        return {}
