"""agent_setup.codex — port of agents/codex/setup.sh.

Configures Codex CLI:
  - Write ~/.codex/AGENTS.md (shared rules.md + codex-specific + baked rules)
  - Copy agents/codex/default.rules → ~/.codex/rules/default.rules
    (refuse to overwrite if live file is larger — user has custom entries)
  - Merge MCP servers into ~/.codex/config.toml ([mcp_servers.<name>] blocks,
    preserving non-mcp_servers sections)
  - Inject statusline.toml content into [tui] section of config.toml
  - Copy agents/codex/hooks.json → ~/.codex/hooks.json
  - deploy_skills(runner, dotfiles_dir, "codex")
  - deploy_subagents(dotfiles_dir, ~/.codex/agents)

All paths are injected; Path.home() MUST NOT appear here.
"""

from __future__ import annotations

import shutil
import tomllib
from collections.abc import Callable
from pathlib import Path

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.agent.lib import (
    StepResult,
    build_global_instructions,
    deploy_skills,
    deploy_subagents,
    mcp_servers_for,
    mcp_skip,
)
from dotfiles.cmd.agent.toml_writer import render_mcp_toml, upsert_section


def setup_codex(
    *,
    runner: ProcessRunner,
    home: Path,
    dotfiles_dir: Path,
    which: Callable[[str], str | None] = shutil.which,  # type: ignore[assignment]
) -> list[StepResult]:
    """Configure Codex CLI. Returns a list of StepResult (one per step)."""
    codex_home = home / ".codex"
    codex_home.mkdir(parents=True, exist_ok=True)

    results: list[StepResult] = []
    results.extend(_setup_instructions(dotfiles_dir, codex_home))
    results.extend(_setup_default_rules(dotfiles_dir, codex_home))
    results.extend(_setup_mcp(dotfiles_dir, codex_home, home))
    results.extend(_ensure_doc_fallback(codex_home))
    results.extend(_setup_statusline(dotfiles_dir, codex_home))
    results.extend(_setup_hooks(dotfiles_dir, codex_home))
    results.append(deploy_skills(runner, dotfiles_dir, "codex", which=which))
    results.extend(deploy_subagents(dotfiles_dir, codex_home / "agents"))
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


_CODEX_SPECIFIC: tuple[str, ...] = (
    "## Codex-Specific",
    "",
    "- This project uses AGENTS.md as the primary instruction file.",
    "- When CODEX.md exists at the project root, it is a symlink to AGENTS.md.",
    "- Follow the same conventions as Claude Code: verify before claiming done,"
    " TDD when tests exist, minimize surface area.",
)


def _setup_instructions(dotfiles_dir: Path, codex_home: Path) -> list[StepResult]:
    """Write ~/.codex/AGENTS.md = core agent instructions + codex-specific block."""
    content = build_global_instructions(dotfiles_dir, extra_sections=_CODEX_SPECIFIC)
    if content is None:
        return []

    (codex_home / "AGENTS.md").write_text(content, encoding="utf-8")
    return [StepResult(level="success", message="Core instructions (~/.codex/AGENTS.md)")]


def _setup_default_rules(dotfiles_dir: Path, codex_home: Path) -> list[StepResult]:
    """Copy agents/codex/default.rules → ~/.codex/rules/default.rules.

    Refuses to overwrite if the live file has more lines than the source
    (user has appended interactively-approved rules) — matches the .sh guard.
    """
    src = dotfiles_dir / "ai" / "agents" / "codex" / "default.rules"
    if not src.is_file():
        return []

    rules_dir = codex_home / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    dest = rules_dir / "default.rules"

    if dest.is_file():
        src_lines = len(src.read_text().splitlines())
        dest_lines = len(dest.read_text().splitlines())
        if dest_lines > src_lines and src.read_bytes() != dest.read_bytes():
            return [
                StepResult(
                    level="success",
                    message=(
                        "~/.codex/rules/default.rules has more lines than dotfiles baseline"
                        " — leaving in place."
                    ),
                    details="Fold new universal rules back into agents/codex/default.rules,"
                    " then re-run.",
                )
            ]

    shutil.copy2(src, dest)
    n = sum(1 for line in dest.read_text().splitlines() if line.startswith("prefix_rule"))
    return [
        StepResult(
            level="success",
            message=f"Deployed {n} command auto-approve rules (~/.codex/rules/default.rules)",
        )
    ]


def _setup_mcp(dotfiles_dir: Path, codex_home: Path, home: Path) -> list[StepResult]:
    """Write [mcp_servers.<name>] TOML blocks into ~/.codex/config.toml.

    Uses upsert_section to replace mcp_servers while preserving other sections
    (marketplaces, projects, plugins, tui, etc.).
    """
    skip = mcp_skip(home)
    # codex setup.sh uses codex | claude targets (claude as fallback)
    servers_codex = mcp_servers_for(dotfiles_dir, "codex", skip=skip)
    servers_claude = mcp_servers_for(dotfiles_dir, "claude", skip=skip)
    # Merge: codex takes priority; add claude targets not already present
    servers: dict[str, object] = {**servers_claude, **servers_codex}

    config_toml = codex_home / "config.toml"
    existing_text = config_toml.read_text() if config_toml.is_file() else ""

    # Validate + strip mcp_servers, preserve rest; then append new blocks
    try:
        new_text = upsert_section(existing_text, servers)  # type: ignore[arg-type]
    except tomllib.TOMLDecodeError:
        # Corrupted config — start fresh with only MCP
        new_text = render_mcp_toml(servers)  # type: ignore[arg-type]

    config_toml.write_text(new_text, encoding="utf-8")
    return [StepResult(level="success", message=f"Configured {len(servers)} MCP servers (Codex)")]


_DOC_FALLBACK_LINE = 'project_doc_fallback_filenames = ["CODEX.md"]'


def _ensure_doc_fallback(codex_home: Path) -> list[StepResult]:
    """Ensure ``project_doc_fallback_filenames = ["CODEX.md"]`` is in config.toml.

    Idempotent — adds only if the key is absent; preserves the existing value
    if the user has customised it. Matches the old codex/setup.sh behaviour
    which always wrote this line when generating config.toml.
    """
    config_toml = codex_home / "config.toml"
    if not config_toml.is_file():
        config_toml.write_text(_DOC_FALLBACK_LINE + "\n", encoding="utf-8")
        return [
            StepResult(level="success", message="Set project_doc_fallback_filenames (CODEX.md)")
        ]

    text = config_toml.read_text()
    try:
        parsed = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        parsed = {}

    if "project_doc_fallback_filenames" in parsed:
        return []  # Already present — idempotent skip

    # Prepend the line so it appears near the top (before MCP blocks)
    config_toml.write_text(_DOC_FALLBACK_LINE + "\n\n" + text, encoding="utf-8")
    return [StepResult(level="success", message="Set project_doc_fallback_filenames (CODEX.md)")]


def _setup_statusline(dotfiles_dir: Path, codex_home: Path) -> list[StepResult]:
    """Inject statusline.toml content into the [tui] section of config.toml.

    Merges the parsed statusline keys into the [tui] table of config.toml,
    replacing any pre-existing theme= or status_line= values. Preserves all
    other sections. Faithful to the awk script: if [tui] is absent, appends it.
    """
    statusline_src = dotfiles_dir / "ai" / "agents" / "codex" / "statusline.toml"
    if not statusline_src.is_file():
        return []

    config_toml = codex_home / "config.toml"
    if not config_toml.is_file():
        config_toml.write_text("", encoding="utf-8")

    statusline_content = statusline_src.read_text()
    existing = config_toml.read_text()

    new_text = _merge_tui_section(existing, statusline_content)
    config_toml.write_text(new_text, encoding="utf-8")
    return [
        StepResult(level="success", message="Configured Codex statusline (~/.codex/config.toml)")
    ]


def _merge_tui_section(toml_text: str, statusline_toml: str) -> str:
    """Merge statusline keys into [tui] in toml_text; append [tui] if absent."""
    try:
        statusline_keys = tomllib.loads(statusline_toml)
    except tomllib.TOMLDecodeError:
        return toml_text

    lines = toml_text.splitlines(keepends=True)
    result = _drop_tui_managed_keys(lines)

    # Find the [tui] header in result
    tui_idx = _find_section_index(result, "[tui]")
    new_lines = _render_tui_keys(statusline_keys)

    if tui_idx is not None:
        # Insert new_lines right after the [tui] header line
        result[tui_idx + 1 : tui_idx + 1] = new_lines
    else:
        # Append a new [tui] section
        if result and result[-1].rstrip("\n\r"):
            result.append("\n")
        result.append("[tui]\n")
        result.extend(new_lines)

    return "".join(result)


_TUI_MANAGED_KEYS = frozenset({"theme", "status_line"})


def _line_key(stripped: str) -> str:
    """Return the TOML key from a ``key = value`` line, or empty string."""
    return stripped.split("=", 1)[0].strip() if "=" in stripped else ""


def _starts_multiline_array(stripped: str) -> bool:
    """True when status_line opens an array that does not close on this line."""
    return _line_key(stripped) == "status_line" and "]" not in stripped


def _drop_tui_managed_keys(lines: list[str]) -> list[str]:
    """Remove theme= and status_line= keys (incl. multi-line arrays) from [tui]."""
    result: list[str] = []
    in_tui = False
    skip_array = False

    for line in lines:
        stripped = line.rstrip("\n\r")
        skip_array, keep = _process_line(stripped, in_tui, skip_array)
        if stripped.startswith("["):
            in_tui = stripped == "[tui]"
        if keep:
            result.append(line)

    return result


def _process_line(stripped: str, in_tui: bool, skip_array: bool) -> tuple[bool, bool]:
    """Return (new_skip_array, keep).

    Decides whether the current line should be kept and whether we enter/exit
    array-skip mode. Extracted to keep _drop_tui_managed_keys under complexity 10.
    """
    if skip_array:
        return ("]" not in stripped), False
    if stripped.startswith("["):
        return False, True
    if in_tui and _line_key(stripped) in _TUI_MANAGED_KEYS:
        return _starts_multiline_array(stripped), False
    return False, True


def _find_section_index(lines: list[str], header: str) -> int | None:
    """Return the index of the line matching *header*, or None."""
    for i, line in enumerate(lines):
        if line.rstrip("\n\r") == header:
            return i
    return None


def _render_tui_keys(keys: dict[str, object]) -> list[str]:
    """Render a dict of simple TOML values as key = value lines."""
    from dotfiles.cmd.agent.toml_writer import _toml_value  # type: ignore[attr-defined]

    return [f"{k} = {_toml_value(v)}\n" for k, v in keys.items()]


def _setup_hooks(dotfiles_dir: Path, codex_home: Path) -> list[StepResult]:
    """Copy agents/codex/hooks.json → ~/.codex/hooks.json."""
    src = dotfiles_dir / "ai" / "agents" / "codex" / "hooks.json"
    if not src.is_file():
        return []
    shutil.copy2(src, codex_home / "hooks.json")
    return [StepResult(level="success", message="Deployed hooks (~/.codex/hooks.json)")]
