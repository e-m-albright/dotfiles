"""Shared helpers ported from agents/shared/lib.sh.

All functions take injected ``home`` / ``dotfiles_dir`` / ``runner`` parameters.
``Path.home()`` MUST NOT appear here — that belongs only in the composition root.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import cast

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.agent.config import load_mcp_servers
from dotfiles.result import StepResult  # re-exported for the vendor adapters

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
    import json as _json

    json_path = dotfiles_dir / "ai" / "agents" / "shared" / "mcp-servers.json"
    if not json_path.exists():
        return {}
    try:
        raw_obj: object = _json.loads(json_path.read_text())
    except (_json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw_obj, dict):
        return {}
    raw_dict = cast(dict[str, object], raw_obj)

    # Use load_mcp_servers for parsed/validated targets info
    entries = load_mcp_servers(json_path)

    result: dict[str, dict[str, object]] = {}
    for name, entry in entries.items():
        if name in skip:
            continue
        if target not in entry.targets:
            continue
        # Retrieve the original raw dict to preserve all fields, then strip targets
        raw_entry = raw_dict.get(name)
        if not isinstance(raw_entry, dict):
            continue
        raw_entry_typed = cast(dict[str, object], raw_entry)
        config: dict[str, object] = {k: v for k, v in raw_entry_typed.items() if k != "targets"}
        result[name] = config

    return result


def all_mcp_server_names(dotfiles_dir: Path) -> set[str]:
    """Return every server name in the MCP registry, regardless of target.

    Used by clean-mode permission pruning to decide which ``mcp__`` permissions
    are still "known". A permission for a cursor-only server (``mcp__context7``)
    must not be pruned from Claude's allow-list just because that server doesn't
    target Claude — mirrors the bash ``jq 'keys[]'`` over the whole registry.
    Excludes ``$``-prefixed meta keys (e.g. ``$comment``).
    """
    import json as _json

    json_path = dotfiles_dir / "ai" / "agents" / "shared" / "mcp-servers.json"
    if not json_path.exists():
        return set()
    try:
        raw: object = _json.loads(json_path.read_text())
    except (_json.JSONDecodeError, OSError):
        return set()
    if not isinstance(raw, dict):
        return set()
    return {k for k in cast(dict[str, object], raw) if not k.startswith("$")}


def merge_managed_mcp(
    existing_mcp: Mapping[str, object],
    servers: Mapping[str, object],
    *,
    managed_keys: set[str],
    reset_mcp: bool,
) -> dict[str, object]:
    """Merge *servers* over *existing_mcp*, honouring ``--reset-mcp``.

    The single source of truth for the merge/purge logic shared by every JSON
    vendor (Claude, Gemini, Cursor, Claude Desktop). When *reset_mcp* is True,
    *managed_keys* are stripped from the existing config first so renamed or
    removed managed servers don't linger; user-added (unmanaged) entries are
    always preserved. Current *servers* always win on key collisions.
    """
    base = (
        {k: v for k, v in existing_mcp.items() if k not in managed_keys}
        if reset_mcp
        else dict(existing_mcp)
    )
    return {**base, **servers}


# ---------------------------------------------------------------------------
# Global instruction file (shared rules.md + baked process rules)
# ---------------------------------------------------------------------------


def build_global_instructions(
    dotfiles_dir: Path,
    *,
    extra_sections: Sequence[str] = (),
) -> str | None:
    """Return the core agent instructions, or None if the kernel doc is absent.

    One hand-authored doc (``agents/shared/rules.md``) is the single source of
    truth, written verbatim to every vendor's instruction file. *extra_sections*
    are appended (Codex uses this for its Codex-specific block). No composition,
    no baking — what you read in rules.md is what each tool gets.
    """
    kernel = dotfiles_dir / "ai" / "agents" / "shared" / "rules.md"
    if not kernel.is_file():
        return None
    parts: list[str] = [kernel.read_text(), *extra_sections]
    return "\n".join(parts)


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
    vendor: str,
    *,
    which: Callable[[str], str | None] = shutil.which,  # type: ignore[assignment]
) -> StepResult:
    """Run ``npx skills add`` to deploy ``ai/skills`` for *vendor*.

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

    cmd = (
        "npx",
        "skills",
        "add",
        str(src),
        "-s",
        "*",
        "-a",
        vendor,
        "-g",
        "-y",
        "--copy",
    )
    result = runner.run(cmd, check=False)
    if result.exit_code == 0:
        return StepResult(level="success", message=f"Deployed skills via npx skills ({vendor})")
    return StepResult(
        level="error",
        message=f"Failed to deploy skills via npx skills ({vendor})",
        details=result.stderr,
    )
