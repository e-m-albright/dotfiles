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
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from dotfiles.logging import get_logger

_log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Config file models
# ---------------------------------------------------------------------------


class McpServerEntry(BaseModel):
    """One entry in agents/shared/mcp-servers.json."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    targets: list[str] = []
    kind: str | None = Field(default=None, alias="type")
    url: str | None = None
    command: str | None = None


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


class McpServersFile(BaseModel):
    """Any agent config projected to just its ``mcpServers`` map (presence check)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    mcp_servers: dict[str, object] = Field(default_factory=dict, alias="mcpServers")


class GeminiTools(BaseModel):
    """The ``tools`` block of ~/.gemini/settings.json (only ``exclude`` matters here)."""

    model_config = ConfigDict(extra="ignore")

    exclude: list[object] | None = None


class GeminiSettings(BaseModel):
    """~/.gemini/settings.json projected to the fields the capability probe reads."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    mcp_servers: dict[str, object] = Field(default_factory=dict, alias="mcpServers")
    tools: GeminiTools = Field(default_factory=GeminiTools)


class PluginInstall(BaseModel):
    """One install record under a plugin ref key."""

    model_config = ConfigDict(extra="ignore")

    version: str = ""


class InstalledPlugins(BaseModel):
    """~/.claude/plugins/installed_plugins.json — the ``plugins`` map."""

    model_config = ConfigDict(extra="ignore")

    plugins: dict[str, list[PluginInstall]] = Field(default_factory=dict)


class ClaudeSettingsProbe(BaseModel):
    """~/.claude/settings.json projected to statusline / hooks / permissions presence."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    status_line: dict[str, object] | None = Field(default=None, alias="statusLine")
    hooks: dict[str, object] = Field(default_factory=dict)
    permissions: PermissionsBlock = Field(default_factory=PermissionsBlock)


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
    except (pydantic.ValidationError, ValueError) as exc:
        _log.warning("config_parse_failed", path=str(path), model=model.__name__, error=str(exc))
        return None


def load_mcp_registry(path: Path) -> tuple[dict[str, McpServerEntry], dict[str, object]]:
    """Read mcp-servers.json once: validated entries plus the raw object-valued dict."""
    if not path.exists():
        return {}, {}
    try:
        raw: object = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        _log.warning("mcp_servers_read_failed", path=str(path), error=str(exc))
        return {}, {}
    if not isinstance(raw, dict):
        _log.warning("mcp_servers_not_object", path=str(path))
        return {}, {}
    raw_dict = cast(dict[str, object], raw)
    obj_only: dict[str, dict[str, object]] = {
        k: cast(dict[str, object], v) for k, v in raw_dict.items() if isinstance(v, dict)
    }
    try:
        return _MCP_SERVERS_ADAPTER.validate_python(obj_only), raw_dict
    except pydantic.ValidationError as exc:
        _log.warning("mcp_servers_invalid", path=str(path), error=str(exc))
        return {}, raw_dict


def load_mcp_servers(path: Path) -> dict[str, McpServerEntry]:
    """Read mcp-servers.json; return only object-valued entries parsed as McpServerEntry."""
    entries, _ = load_mcp_registry(path)
    return entries
