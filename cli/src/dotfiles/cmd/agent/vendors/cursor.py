"""agent_setup.cursor — Cursor agentic setup.

Configures Cursor agentic setup:
  - Merge shared MCP servers into dotfiles_dir/editors/cursor/mcp.json (IN-REPO)
  - Generate dotfiles_dir/ai/agents/cursor/rules/shared-rules.mdc (kernel + YAML frontmatter)
  - Symlink dotfiles_dir/ai/agents/cursor/cli-config.json → home/.cursor/cli-config.json
  - Symlink dotfiles_dir/ai/agents/cursor → home/.cursor/plugins/dotfiles
  - Generate dotfiles_dir/editors/cursor/.cursorignore from shared ignore-patterns

All paths are injected; Path.home() MUST NOT appear here.
NOTE: cursor's MCP target is IN-REPO (dotfiles_dir/editors/cursor/mcp.json), NOT home.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import cast

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.agent.lib import (
    StepResult,
    deploy_subagents,
    disabled_mcp_server_names,
    mcp_servers_for,
    mcp_skip,
    merge_managed_mcp,
)
from dotfiles.cmd.agent.settings_merger import (
    load_json_or,
    merge_replace,
    write_json_safely,
)
from dotfiles.fsutil import symlink

_CURSORIGNORE_HEADER = """\
# Cursor ignore file
# AUTO-GENERATED from agents/shared/ignore-patterns + Cursor-specific additions
# Do not edit directly — modify agents/shared/ignore-patterns instead

"""

_CURSORIGNORE_CURSOR_SPECIFIC = """
# Cursor-specific
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
Thumbs.db
.cache/
"""


def setup_cursor(
    *,
    runner: ProcessRunner,
    home: Path,
    dotfiles_dir: Path,
    reset_mcp: bool = False,
    which: Callable[[str], str | None] = shutil.which,
) -> list[StepResult]:
    """Configure Cursor agentic setup. Returns a list of StepResult."""
    results: list[StepResult] = []
    results.extend(_setup_mcp(dotfiles_dir, home, reset_mcp=reset_mcp))
    results.extend(_setup_rules(dotfiles_dir))
    # Cursor 2.4+ reads ~/.cursor/agents — deploy our shared subagents there too.
    results.extend(deploy_subagents(dotfiles_dir, home / ".cursor" / "agents"))
    results.extend(_setup_cli_config(dotfiles_dir, home))
    results.extend(_setup_plugin(dotfiles_dir, home))
    results.extend(_setup_cursorignore(dotfiles_dir))
    results.extend(_plugin_reminder(dotfiles_dir))
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _setup_mcp(dotfiles_dir: Path, home: Path, *, reset_mcp: bool = False) -> list[StepResult]:
    """Merge shared MCP servers into editors/cursor/mcp.json (in-repo).

    When *reset_mcp* is True, purge any managed keys (names from
    ``mcp_servers_for(dotfiles_dir, "cursor")``) from the existing config before
    merging the current set — faithful to the ``--reset-mcp`` branch in
    agents/cursor/setup.sh.
    """
    mcp_file = dotfiles_dir / "editors" / "cursor" / "mcp.json"
    mcp_file.parent.mkdir(parents=True, exist_ok=True)

    skip = mcp_skip(home)
    servers = mcp_servers_for(dotfiles_dir, "cursor", skip=skip)

    existing = load_json_or(mcp_file, {})
    raw_mcp = existing.get("mcpServers", {})
    existing_mcp: dict[str, object] = (
        cast(dict[str, object], raw_mcp) if isinstance(raw_mcp, dict) else {}
    )

    merged_mcp = merge_managed_mcp(
        existing_mcp,
        servers,
        managed_keys=set(mcp_servers_for(dotfiles_dir, "cursor").keys()),
        reset_mcp=reset_mcp,
        prune=disabled_mcp_server_names(dotfiles_dir),
    )
    updated = merge_replace(existing, ["mcpServers"], merged_mcp)
    write_json_safely(mcp_file, updated)

    return [
        StepResult(
            level="success", message=f"Configured {len(servers)} MCP servers (Cursor, in-repo)"
        )
    ]


def _setup_rules(dotfiles_dir: Path) -> list[StepResult]:
    """Generate agents/cursor/rules/shared-rules.mdc with YAML frontmatter."""
    shared_rules = dotfiles_dir / "ai" / "agents" / "shared" / "rules.md"
    if not shared_rules.is_file():
        return []

    rules_dir = dotfiles_dir / "ai" / "agents" / "cursor" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    rules_content = shared_rules.read_text()
    content = (
        "---\n"
        "description: Shared agentic guardrails — process, safety, context, testing\n"
        "alwaysApply: true\n"
        "---\n"
        "\n"
        f"{rules_content}"
    )

    (rules_dir / "shared-rules.mdc").write_text(content, encoding="utf-8")
    return [StepResult(level="success", message="Generated rules/shared-rules.mdc")]


def _setup_cli_config(dotfiles_dir: Path, home: Path) -> list[StepResult]:
    """Symlink agents/cursor/cli-config.json → home/.cursor/cli-config.json."""
    src = dotfiles_dir / "ai" / "agents" / "cursor" / "cli-config.json"
    if not src.is_file():
        return []
    symlink(src, home / ".cursor" / "cli-config.json")
    return [StepResult(level="success", message="Deployed cli-config.json")]


def _setup_plugin(dotfiles_dir: Path, home: Path) -> list[StepResult]:
    """Symlink agents/cursor → home/.cursor/plugins/dotfiles."""
    src = dotfiles_dir / "ai" / "agents" / "cursor"
    dest = home / ".cursor" / "plugins" / "dotfiles"
    if dest.is_symlink() and dest.resolve() == src.resolve():
        return [StepResult(level="success", message="Plugin already registered")]
    symlink(src, dest)
    return [
        StepResult(
            level="success", message="Registered dotfiles plugin (~/.cursor/plugins/dotfiles)"
        )
    ]


def _plugin_reminder(dotfiles_dir: Path) -> list[StepResult]:
    """Remind that Cursor Marketplace plugins install manually via /add-plugin in Cursor chat.

    Cursor plugins can't be installed from the CLI, so this is a next-step nudge rather
    than an action. PLUGINS.md is the source of truth for the full per-profile matrix.
    """
    plugins_doc = dotfiles_dir / "ai" / "agents" / "cursor" / "PLUGINS.md"
    if not plugins_doc.is_file():
        return []
    return [
        StepResult(
            level="info",
            message="Marketplace plugins are manual — in Cursor chat run "
            "/add-plugin superpowers, then context7-plugin",
            details=f"parallel optional · full matrix: {plugins_doc}",
        )
    ]


def _setup_cursorignore(dotfiles_dir: Path) -> list[StepResult]:
    """Generate editors/cursor/.cursorignore from shared ignore-patterns."""
    ignore_src = dotfiles_dir / "ai" / "agents" / "shared" / "ignore-patterns"
    if not ignore_src.is_file():
        return []

    cursor_ignore = dotfiles_dir / "editors" / "cursor" / ".cursorignore"
    cursor_ignore.parent.mkdir(parents=True, exist_ok=True)

    content = _CURSORIGNORE_HEADER + ignore_src.read_text() + _CURSORIGNORE_CURSOR_SPECIFIC
    cursor_ignore.write_text(content, encoding="utf-8")
    return [StepResult(level="success", message="Generated .cursorignore")]
