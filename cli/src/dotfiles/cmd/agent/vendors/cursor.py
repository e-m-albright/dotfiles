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

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.agent.lib import (
    StepResult,
    deploy_subagents,
    merge_mcp_json_file,
)
from dotfiles.fsutil import prune_broken_symlinks, symlink

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
    results.extend(_setup_skills(dotfiles_dir, home))
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
    """Merge shared MCP servers into editors/cursor/mcp.json (in-repo)."""
    mcp_file = dotfiles_dir / "editors" / "cursor" / "mcp.json"
    mcp_file.parent.mkdir(parents=True, exist_ok=True)
    return merge_mcp_json_file(
        mcp_file,
        dotfiles_dir,
        "cursor",
        home,
        reset_mcp=reset_mcp,
        success_message="Configured MCP servers (Cursor, in-repo)",
    )


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


def _setup_skills(dotfiles_dir: Path, home: Path) -> list[StepResult]:
    """Symlink canonical skills into Cursor's user skill dir.

    Cursor's vendor built-ins live in ~/.cursor/skills-cursor. Our portable,
    repo-owned skills belong in ~/.cursor/skills. The public `skills` CLI does
    not currently mirror all canonical skills for Cursor reliably on this
    machine, so use explicit symlinks from the dotfiles source of truth.
    """
    src = dotfiles_dir / "ai" / "skills"
    shared = home / ".agents" / "skills"
    if not src.is_dir() and not shared.is_dir():
        return []

    dest = home / ".cursor" / "skills"
    dest.mkdir(parents=True, exist_ok=True)
    prune_broken_symlinks(dest)

    # Canonical repo skills first, then any shared/external skills not already linked.
    linked: set[str] = set()
    return [
        *_link_skills_into(src, dest, "skill", linked),
        *_link_skills_into(shared, dest, "external skill", linked),
    ]


def _link_skills_into(source: Path, dest: Path, label: str, linked: set[str]) -> list[StepResult]:
    """Symlink each ``*/SKILL.md`` dir under *source* into *dest*, skipping names
    already in *linked* (and recording new ones there so later sources don't double-link)."""
    if not source.is_dir():
        return []
    results: list[StepResult] = []
    for skill_md in sorted(source.glob("*/SKILL.md")):
        name = skill_md.parent.name
        if name in linked:
            continue
        symlink(skill_md.parent, dest / name)
        linked.add(name)
        results.append(StepResult(level="success", message=f"Linked Cursor {label} {name}"))
    return results


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
            message="Marketplace plugins are manual — no required Cursor plugins; "
            "install /add-plugin parallel only when needed",
            details=f"full matrix: {plugins_doc}",
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
