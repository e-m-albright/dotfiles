"""agent_setup.gemini — port of agents/gemini/setup.sh.

Configures Gemini CLI:
  - Seed ~/.gemini/settings.json from dotfiles seed if missing
  - Merge managed MCP servers into settings.json
  - Write ~/.gemini/GEMINI.md (rules.md + baked rules)

All paths are injected; Path.home() MUST NOT appear here.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import cast

from dotfiles.core.agent_setup.lib import (
    StepResult,
    baked_rule_count,
    build_global_instructions,
    mcp_servers_for,
    mcp_skip,
    merge_managed_mcp,
)
from dotfiles.core.agent_setup.settings_merger import (
    load_json_or,
    merge_replace,
    write_json_safely,
)
from dotfiles.core.ports import ProcessRunner


def setup_gemini(
    *,
    runner: ProcessRunner,
    home: Path,
    dotfiles_dir: Path,
    reset_mcp: bool = False,
    which: Callable[[str], str | None] = shutil.which,  # type: ignore[assignment]
) -> list[StepResult]:
    """Configure Gemini CLI. Returns a list of StepResult (one per step)."""
    if which("gemini") is None:
        return [StepResult(ok=True, message="skipped — gemini not installed")]

    gemini_home = home / ".gemini"
    gemini_home.mkdir(parents=True, exist_ok=True)

    results: list[StepResult] = []
    results.extend(_setup_settings_and_mcp(dotfiles_dir, gemini_home, reset_mcp=reset_mcp))
    results.extend(_setup_instructions(dotfiles_dir, gemini_home))
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _setup_settings_and_mcp(
    dotfiles_dir: Path, gemini_home: Path, *, reset_mcp: bool = False
) -> list[StepResult]:
    """Seed settings.json if missing, then merge managed MCP servers.

    When *reset_mcp* is True, purge managed keys (names from
    ``mcp_servers_for(dotfiles_dir, "gemini")``) from the existing config before
    merging the current set — faithful to the ``--reset-mcp`` branch in
    agents/gemini/setup.sh.
    """
    settings_file = gemini_home / "settings.json"
    seed = dotfiles_dir / "agents" / "gemini" / "settings.json"

    if not settings_file.exists() and seed.is_file():
        import shutil as _shutil

        _shutil.copy2(seed, settings_file)

    skip = mcp_skip(gemini_home.parent)  # home = gemini_home.parent
    servers = mcp_servers_for(dotfiles_dir, "gemini", skip=skip)

    existing = load_json_or(settings_file, {})
    raw_mcp = existing.get("mcpServers", {})
    existing_mcp: dict[str, object] = (
        cast(dict[str, object], raw_mcp) if isinstance(raw_mcp, dict) else {}
    )

    merged_mcp = merge_managed_mcp(
        existing_mcp,
        servers,
        managed_keys=set(mcp_servers_for(dotfiles_dir, "gemini").keys()),
        reset_mcp=reset_mcp,
    )
    updated = merge_replace(existing, ["mcpServers"], merged_mcp)
    write_json_safely(settings_file, updated)

    return [StepResult(ok=True, message=f"Configured {len(servers)} MCP servers (Gemini)")]


def _setup_instructions(dotfiles_dir: Path, gemini_home: Path) -> list[StepResult]:
    """Write ~/.gemini/GEMINI.md = rules.md header + baked rules."""
    content = build_global_instructions(dotfiles_dir)
    if content is None:
        return []

    (gemini_home / "GEMINI.md").write_text(content, encoding="utf-8")
    rule_count = baked_rule_count(dotfiles_dir)
    return [
        StepResult(
            ok=True,
            message=f"Global instructions + {rule_count} baked rules (~/.gemini/GEMINI.md)",
        )
    ]
