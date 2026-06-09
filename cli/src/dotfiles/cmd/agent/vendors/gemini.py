"""agent_setup.gemini — the ~/.gemini-config slot (now Antigravity CLI `agy`).

Gemini CLI sunsets for Pro/Ultra/free on 2026-06-18; its successor, Google's
Antigravity CLI (`agy`, brew cask ``antigravity-cli``), reads the **same
~/.gemini/ config** (settings.json mcpServers + tools.exclude, AGENTS.md /
GEMINI.md), so this module migrates by swapping the binary check and writing the
portable AGENTS.md. (The vendor key stays "gemini" until the registry rename;
agy is what actually consumes this config.)

Configures the slot:
  - Seed ~/.gemini/settings.json from dotfiles seed if missing
  - Merge managed MCP servers into settings.json (+ tools.exclude blocklist)
  - Write ~/.gemini/AGENTS.md (the shared rules.md kernel, verbatim); retire GEMINI.md

All paths are injected; Path.home() MUST NOT appear here.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import cast

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.agent.lib import (
    StepResult,
    build_global_instructions,
    mcp_servers_for,
    mcp_skip,
    merge_managed_mcp,
)
from dotfiles.cmd.agent.settings_merger import (
    load_json_or,
    merge_replace,
    write_json_safely,
)


def setup_gemini(
    *,
    runner: ProcessRunner,
    home: Path,
    dotfiles_dir: Path,
    reset_mcp: bool = False,
    which: Callable[[str], str | None] = shutil.which,
) -> list[StepResult]:
    """Configure the ~/.gemini slot (Antigravity `agy`). Returns a list of StepResult."""
    if which("agy") is None and which("gemini") is None:
        return [StepResult(level="success", message="skipped — agy/gemini not installed")]

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
    seed = dotfiles_dir / "ai" / "agents" / "gemini" / "settings.json"

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

    # Deploy the managed shell-command blocklist (tools.exclude) from the seed.
    # `seed-if-missing` above doesn't refresh an existing install, so set it
    # explicitly here. exclude is a blocklist mirroring deny-commands.yaml; we
    # never touch tools.core (setting it would disable unlisted built-in tools).
    managed_exclude = _managed_tool_excludes(seed)
    results: list[StepResult] = []
    if managed_exclude is not None:
        updated = merge_replace(updated, ["tools", "exclude"], managed_exclude)
        results.append(
            StepResult(
                level="success", message=f"Blocked {len(managed_exclude)} shell commands (Gemini)"
            )
        )

    write_json_safely(settings_file, updated)
    results.append(
        StepResult(level="success", message=f"Configured {len(servers)} MCP servers (Gemini)")
    )
    return results


def _managed_tool_excludes(seed: Path) -> list[str] | None:
    """Read the managed tools.exclude list from the dotfiles seed, if present."""
    if not seed.is_file():
        return None
    seed_data: dict[str, object] = load_json_or(seed, {})
    tools = seed_data.get("tools")
    if not isinstance(tools, dict):
        return None
    exclude = cast("dict[str, object]", tools).get("exclude")
    if not isinstance(exclude, list):
        return None
    return [str(item) for item in cast("list[object]", exclude)]


def _setup_instructions(dotfiles_dir: Path, gemini_home: Path) -> list[StepResult]:
    """Write ~/.gemini/AGENTS.md = core agent instructions (portable, agy-read).

    AGENTS.md is the cross-vendor standard (Codex/Pi use it too) and what we
    deploy. We retire any ~/.gemini/GEMINI.md so it can't out-rank AGENTS.md
    (agy reads both; GEMINI.md wins precedence) and to keep one source of truth.
    """
    content = build_global_instructions(dotfiles_dir)
    if content is None:
        return []

    (gemini_home / "AGENTS.md").write_text(content, encoding="utf-8")
    stale_gemini_md = gemini_home / "GEMINI.md"
    if stale_gemini_md.exists():
        stale_gemini_md.unlink()
    return [StepResult(level="success", message="Core instructions (~/.gemini/AGENTS.md)")]
