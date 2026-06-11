"""Shared helpers ported from agents/shared/lib.sh.

All functions take injected ``home`` / ``dotfiles_dir`` / ``runner`` parameters.
``Path.home()`` MUST NOT appear here — that belongs only in the composition root.
"""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Callable, Collection, Mapping, Sequence
from pathlib import Path
from typing import cast

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.agent.config import McpServerEntry, load_mcp_registry
from dotfiles.cmd.agent.settings_merger import (
    load_json_or,
    merge_replace,
    write_json_safely,
)
from dotfiles.logging import get_logger
from dotfiles.result import StepResult  # re-exported for the agent adapters

_log = get_logger(__name__)

# ---------------------------------------------------------------------------
# MCP helpers
# ---------------------------------------------------------------------------


def _parse_csv_names(raw: str) -> set[str]:
    """Parse a comma-separated string of names, stripping whitespace and blanks."""
    return {part.strip() for part in raw.split(",") if part.strip()}


def _read_skip_file(path: Path) -> set[str]:
    """Read names from a skip file (one per line; ``#`` comment lines ignored)."""
    if not path.is_file():
        return set()
    names: set[str] = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.add(line)
    return names


def mcp_skip(home: Path, *, env: dict[str, str] | None = None) -> set[str]:
    """Return the set of MCP server names to skip.

    Sources (both merged, matching lib.sh behaviour):
    - ``MCP_SKIP`` environment variable (comma-separated)
    - ``home/.config/dotfiles/mcp-skip`` file (one name per line, ``#`` comments stripped)
    """
    env_map = env if env is not None else dict(os.environ)
    names = _parse_csv_names(env_map.get("MCP_SKIP", ""))
    names |= _read_skip_file(home / ".config" / "dotfiles" / "mcp-skip")
    return names


def mcp_servers_for(
    dotfiles_dir: Path,
    target: str,
    *,
    skip: frozenset[str] | set[str] = frozenset(),
) -> dict[str, dict[str, object]]:
    """Return MCP server configs for *target* with ``.targets`` key stripped.

    Mirrors ``mcp_servers_for()`` from lib.sh:
    - Loads ``dotfiles_dir/agents/shared/mcp-servers.json``
    - Filters to entries whose ``.targets`` list includes *target*
    - Removes any entry whose name is in *skip*
    - Strips the ``.targets`` key from each returned config dict
    """
    json_path = dotfiles_dir / "ai" / "agents" / "shared" / "mcp-servers.json"
    entries, raw_dict = load_mcp_registry(json_path)
    if not entries:
        return {}

    result: dict[str, dict[str, object]] = {}
    for name, entry in entries.items():
        config = _targeted_server_config(name, entry, target, skip, raw_dict)
        if config is not None:
            result[name] = config
    return result


def _targeted_server_config(
    name: str,
    entry: McpServerEntry,
    target: str,
    skip: frozenset[str] | set[str],
    raw_dict: dict[str, object],
) -> dict[str, object] | None:
    """The raw server config (``targets`` stripped) iff *name* serves *target* and isn't skipped."""
    if name in skip or target not in entry.targets:
        return None
    raw_entry = raw_dict.get(name)
    if not isinstance(raw_entry, dict):
        return None
    raw_entry_typed = cast(dict[str, object], raw_entry)
    return {k: v for k, v in raw_entry_typed.items() if k != "targets"}


def all_mcp_server_names(dotfiles_dir: Path) -> set[str]:
    """Return every server name in the MCP registry, regardless of target.

    Used by clean-mode permission pruning to decide which ``mcp__`` permissions
    are still "known". A permission for a cursor-only server (``mcp__context7``)
    must not be pruned from Claude's allow-list just because that server doesn't
    target Claude — mirrors the bash ``jq 'keys[]'`` over the whole registry.
    Excludes ``$``-prefixed meta keys (e.g. ``$comment``).
    """
    json_path = dotfiles_dir / "ai" / "agents" / "shared" / "mcp-servers.json"
    _, raw_dict = load_mcp_registry(json_path)
    if not raw_dict:
        return set()
    return {k for k in raw_dict if not k.startswith("$")}


def disabled_mcp_server_names(dotfiles_dir: Path) -> set[str]:
    """Names of servers explicitly retired in the registry (``_<name>_disabled`` keys).

    A disabled entry records a server we *used* to deploy and now want **gone**.
    These are always pruned from live configs on setup, so a retired server
    (e.g. context7 → the ctx7 CLI) doesn't linger as "unmanaged" — keeping
    deploy = mirror, not append.
    """
    names: set[str] = set()
    for key in all_mcp_server_names(dotfiles_dir):  # includes the _<name>_disabled keys
        match = re.fullmatch(r"_(.+)_disabled", key)
        if match:
            names.add(match.group(1))
    return names


def merge_managed_mcp(
    existing_mcp: Mapping[str, object],
    servers: Mapping[str, object],
    *,
    managed_keys: set[str],
    reset_mcp: bool,
    prune: Collection[str] = (),
) -> dict[str, object]:
    """Merge *servers* over *existing_mcp*, honouring ``--reset-mcp`` and *prune*.

    The single source of truth for the merge/purge logic shared by every JSON
    agent (Claude, Gemini, Cursor, Claude Desktop). *prune* names (retired
    servers) are **always** dropped from the existing config. When *reset_mcp*
    is True, *managed_keys* are also stripped so renamed/removed managed servers
    don't linger; otherwise user-added (unmanaged) entries are preserved.
    Current *servers* always win on key collisions.
    """
    base = {
        k: v
        for k, v in existing_mcp.items()
        if k not in prune and not (reset_mcp and k in managed_keys)
    }
    return {**base, **servers}


def merge_mcp_into_json(
    existing: dict[str, object],
    dotfiles_dir: Path,
    target: str,
    home: Path,
    *,
    reset_mcp: bool,
) -> tuple[dict[str, object], int]:
    """Return (*settings* with ``mcpServers`` merged, server count). Does not write."""
    skip = mcp_skip(home)
    servers = mcp_servers_for(dotfiles_dir, target, skip=skip)
    raw_mcp = existing.get("mcpServers", {})
    existing_mcp = cast(dict[str, object], raw_mcp) if isinstance(raw_mcp, dict) else {}
    merged_mcp = merge_managed_mcp(
        existing_mcp,
        servers,
        managed_keys=set(mcp_servers_for(dotfiles_dir, target).keys()),
        reset_mcp=reset_mcp,
        prune=disabled_mcp_server_names(dotfiles_dir),
    )
    return merge_replace(existing, ["mcpServers"], merged_mcp), len(servers)


def merge_mcp_json_file(
    path: Path,
    dotfiles_dir: Path,
    target: str,
    home: Path,
    *,
    reset_mcp: bool,
    success_message: str,
) -> list[StepResult]:
    """Merge managed MCP servers into a JSON config's ``mcpServers`` key."""
    existing = load_json_or(path, {})
    updated, count = merge_mcp_into_json(existing, dotfiles_dir, target, home, reset_mcp=reset_mcp)
    write_json_safely(path, updated)
    return [StepResult(level="success", message=f"{success_message} ({count} servers)")]


# ---------------------------------------------------------------------------
# Global instruction file (shared rules.md + rendered process rules)
# ---------------------------------------------------------------------------


def build_global_instructions(
    dotfiles_dir: Path,
    *,
    extra_sections: Sequence[str] = (),
) -> str | None:
    """Return the core agent instructions, or None if the kernel doc is absent.

    One hand-authored doc (``agents/shared/rules.md``) is the single source of
    truth, written verbatim to every agent's instruction file. *extra_sections*
    are appended (Codex uses this for its Codex-specific block). No composition,
    no baking — what you read in rules.md is what each tool gets.
    """
    kernel = dotfiles_dir / "ai" / "agents" / "shared" / "rules.md"
    if not kernel.is_file():
        return None
    parts: list[str] = [kernel.read_text(), *extra_sections]
    return "\n".join(parts)


def write_kernel_instructions(
    dest: Path,
    dotfiles_dir: Path,
    *,
    extra_sections: Sequence[str] = (),
    message: str,
    missing_error: bool = False,
) -> list[StepResult]:
    """Write the shared rules kernel to *dest*, or report missing/error."""
    content = build_global_instructions(dotfiles_dir, extra_sections=extra_sections)
    if content is None:
        if missing_error:
            return [StepResult(level="error", message="No agents/shared/rules.md found")]
        return []
    dest.write_text(content, encoding="utf-8")
    return [StepResult(level="success", message=message)]


# ---------------------------------------------------------------------------
# Subagent deployment
# ---------------------------------------------------------------------------


def deploy_subagents(dotfiles_dir: Path, dest_dir: Path) -> list[StepResult]:
    """Copy ``dotfiles_dir/ai/subagents/*.md`` into ``dest_dir``.

    Returns a list of StepResult (one per file copied, or one error).
    Mirrors ``deploy_subagents()`` from lib.sh.
    """
    src = dotfiles_dir / "ai" / "subagents"
    if not src.is_dir():
        return []

    dest_dir.mkdir(parents=True, exist_ok=True)
    results: list[StepResult] = []
    for agent in sorted(src.glob("*.md")):
        if not agent.is_file():
            continue
        dest = dest_dir / agent.name
        shutil.copy2(agent, dest)
        results.append(StepResult(level="success", message=f"Deployed subagent {agent.name}"))

    return results


# ---------------------------------------------------------------------------
# Skills deployment
# ---------------------------------------------------------------------------


def deploy_skills(
    runner: ProcessRunner,
    dotfiles_dir: Path,
    agent: str,
    *,
    which: Callable[[str], str | None] = shutil.which,
) -> StepResult:
    """Run ``npx skills add`` to deploy ``ai/skills`` for *agent*.

    The ``-g``/``--copy`` flags are load-bearing (required by the skills CLI).
    Mirrors ``deploy_skills()`` from lib.sh.

    ``which`` is injected so tests can simulate npx being absent without
    touching the real filesystem.
    """
    src = dotfiles_dir / "ai" / "skills"
    if not src.is_dir():
        return StepResult(
            level="error", message="Skills source directory not found", details=str(src)
        )

    if which("npx") is None:
        return StepResult(
            level="error",
            message="npx not found — cannot deploy skills",
            details="Install Node.js to enable skill deployment",
        )

    # `npx skills add --copy` skips any skill whose destination dir already
    # exists, so an edited skill silently keeps its stale deployed copy. Remove
    # our skills first (by name — never `-s '*'`, which would also delete
    # externally-installed skills like superpowers), then add fresh. check=False:
    # a first-time deploy has nothing to remove and remove may exit non-zero.
    skill_names = sorted(p.parent.name for p in src.glob("*/SKILL.md"))
    if skill_names:
        runner.run(
            ("npx", "skills", "remove", *skill_names, "-a", agent, "-g", "-y"),
            check=False,
        )

    cmd = (
        "npx",
        "skills",
        "add",
        str(src),
        "-s",
        "*",
        "-a",
        agent,
        "-g",
        "-y",
        "--copy",
    )
    _log.info("deploy_skills_start", agent=agent, skills=len(skill_names))
    result = runner.run(cmd, check=False)
    if result.exit_code == 0:
        return StepResult(level="success", message=f"Deployed skills via npx skills ({agent})")
    _log.warning("deploy_skills_failed", agent=agent, exit_code=result.exit_code)
    return StepResult(
        level="error",
        message=f"Failed to deploy skills via npx skills ({agent})",
        details=result.stderr,
    )
