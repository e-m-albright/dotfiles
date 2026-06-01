"""Tool discovery registry — reads agents/shared/tool-targets.json.

Faithful port of the jq-based registry queries in setup_tool_symlinks() /
generate_root_symlinks() from prompts/scaffold.sh.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

_REGISTRY_REL = "agents/shared/tool-targets.json"


class ToolTarget(BaseModel):
    """One entry from the tool-targets registry.

    Field names use snake_case; aliases match the camelCase JSON keys.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    rules_dir: str | None = Field(None, alias="rulesDir")
    suffix: str | None = None
    strategy: str | None = None
    symlink_prefix: str | None = Field(None, alias="symlinkPrefix")
    root_file: str | None = Field(None, alias="rootFile")
    agents_md_aware: bool = Field(False, alias="agentsMdAware")


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_registry(dotfiles_dir: Path) -> dict[str, ToolTarget]:
    """Load the tool-targets registry from *dotfiles_dir*.

    Returns an empty dict (graceful degradation) if the file is absent or
    malformed — mirrors the jq fallback in scaffold.sh.
    """
    registry_path = dotfiles_dir / _REGISTRY_REL
    if not registry_path.is_file():
        return {}
    try:
        raw = json.loads(registry_path.read_text())
        tools_raw: dict[str, object] = raw.get("tools", {})
        return {name: ToolTarget.model_validate(data) for name, data in tools_raw.items()}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Filter helpers
# ---------------------------------------------------------------------------


def tools_for_filter(
    registry: dict[str, ToolTarget],
    tools_filter: str,
    *,
    strategy: str = "symlink",
) -> dict[str, ToolTarget]:
    """Return the subset of registry entries matching *tools_filter*.

    - ``"all"`` → all entries with the given strategy
    - comma-separated list → only those names (if they have the strategy)

    Mirrors the jq filter logic in setup_tool_symlinks() / generate_root_symlinks().
    """
    if tools_filter == "all":
        return {k: v for k, v in registry.items() if v.strategy == strategy}

    requested = {name.strip() for name in tools_filter.split(",") if name.strip()}
    return {k: v for k, v in registry.items() if k in requested and v.strategy == strategy}
