"""Shared helpers ported from agents/shared/lib.sh.

All functions take injected ``home`` / ``dotfiles_dir`` / ``runner`` parameters.
``Path.home()`` MUST NOT appear here — that belongs only in the composition root.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from dotfiles.core.agent_config import load_mcp_servers
from dotfiles.core.agent_setup.bake_rules import bake_rules
from dotfiles.core.ports import ProcessRunner

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    """Outcome of a single deployment step."""

    ok: bool
    message: str
    details: str = ""


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

    json_path = dotfiles_dir / "agents" / "shared" / "mcp-servers.json"
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
    """Assemble the global instruction file body, or None if rules.md is absent.

    The single source of truth for the ``# Global Agent Instructions`` file that
    Codex, Gemini, and Pi each write to their own root path. *extra_sections* are
    inserted verbatim between the shared ``rules.md`` and the baked process rules
    (Codex uses this for its Codex-Specific block). Keeping one assembler here
    stops the three vendors' output from drifting apart.
    """
    global_rules = dotfiles_dir / "agents" / "shared" / "rules.md"
    if not global_rules.is_file():
        return None

    parts: list[str] = ["# Global Agent Instructions", "", global_rules.read_text(), ""]
    parts.extend(extra_sections)
    baked = bake_rules(dotfiles_dir)
    if baked:
        parts.append(baked)
    return "\n".join(parts)


def baked_rule_count(dotfiles_dir: Path) -> int:
    """Count the process rules that ``build_global_instructions`` will bake in."""
    return len(list((dotfiles_dir / ".ai" / "rules" / "process").glob("*.mdc")))


# ---------------------------------------------------------------------------
# Subagent deployment
# ---------------------------------------------------------------------------


def deploy_subagents(dotfiles_dir: Path, dest_dir: Path) -> list[StepResult]:
    """Copy ``dotfiles_dir/.ai/agents/*.md`` into ``dest_dir``.

    Returns a list of StepResult (one per file copied, or one error).
    Mirrors ``deploy_subagents()`` from lib.sh.
    """
    src = dotfiles_dir / ".ai" / "agents"
    if not src.is_dir():
        return []

    dest_dir.mkdir(parents=True, exist_ok=True)
    results: list[StepResult] = []
    for agent in sorted(src.glob("*.md")):
        if not agent.is_file():
            continue
        dest = dest_dir / agent.name
        shutil.copy2(agent, dest)
        results.append(StepResult(ok=True, message=f"Deployed subagent {agent.name}"))

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
    """Run ``npx skills add`` to deploy ``.ai/skills`` for *vendor*.

    The ``-g``/``--copy`` flags are load-bearing (required by the skills CLI).
    Mirrors ``deploy_skills()`` from lib.sh.

    ``which`` is injected so tests can simulate npx being absent without
    touching the real filesystem.
    """
    src = dotfiles_dir / ".ai" / "skills"
    if not src.is_dir():
        return StepResult(ok=False, message="Skills source directory not found", details=str(src))

    if which("npx") is None:
        return StepResult(
            ok=False,
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
        return StepResult(ok=True, message=f"Deployed skills via npx skills ({vendor})")
    return StepResult(
        ok=False,
        message=f"Failed to deploy skills via npx skills ({vendor})",
        details=result.stderr,
    )


# ---------------------------------------------------------------------------
# Process-rules symlinking
# ---------------------------------------------------------------------------


def _clean_stale_rule_links(dest_dir: Path, other_suffix: str) -> None:
    """Remove symlinks in dest_dir that use the old suffix (suffix-migration cleanup)."""
    for stale in dest_dir.glob(f"*{other_suffix}"):
        if stale.is_symlink():
            stale.unlink()


def _is_managed_rule_link(link: Path, src: Path) -> bool:
    """True if *link* is a symlink we own — i.e. it points directly into *src*.

    Checked via the link target, not its resolved file, so a dangling link to a
    deleted rule still counts as managed (and therefore prunable).
    """
    if not link.is_symlink():
        return False
    target = link.readlink()
    if not target.is_absolute():
        target = link.parent / target
    try:
        return target.parent.resolve() == src.resolve()
    except OSError:
        return False


def _prune_orphaned_rule_links(dest_dir: Path, src: Path, valid_stems: set[str]) -> None:
    """Remove managed symlinks whose source rule no longer exists in *src*.

    Without this, retiring a process rule leaves a dangling ``<name>`` symlink in
    every vendor's rules dir on the next setup — the suffix-migration cleanup only
    catches the *other* suffix, not same-suffix orphans.
    """
    for link in dest_dir.iterdir():
        if link.stem not in valid_stems and _is_managed_rule_link(link, src):
            link.unlink()


def _symlink_rule(rule: Path, dest_path: Path) -> StepResult:
    """Ensure dest_path → rule symlink exists and is correct. Idempotent."""
    link_name = dest_path.name
    if dest_path.is_symlink() and dest_path.resolve() == rule.resolve():
        return StepResult(ok=True, message=f"Already linked {link_name}")
    if dest_path.is_symlink() or dest_path.exists():
        dest_path.unlink()
    dest_path.symlink_to(rule)
    return StepResult(ok=True, message=f"Symlinked {link_name}")


def symlink_process_rules(
    dotfiles_dir: Path,
    dest_dir: Path,
    suffix: str,
) -> list[StepResult]:
    """Symlink each ``dotfiles_dir/.ai/rules/process/*.mdc`` into ``dest_dir``.

    Link names use *suffix* (e.g. ``".md"`` for Claude Code, ``".mdc"`` for Cursor).
    Stale links with the *other* suffix are cleaned up first, matching the
    suffix-migration safety logic in lib.sh.

    Mirrors ``symlink_process_rules()`` from lib.sh.
    """
    src = dotfiles_dir / ".ai" / "rules" / "process"
    if not src.is_dir():
        return [StepResult(ok=False, message=f"No process rules at {src}")]

    dest_dir.mkdir(parents=True, exist_ok=True)
    other_suffix = ".mdc" if suffix == ".md" else ".md"
    _clean_stale_rule_links(dest_dir, other_suffix)

    rules = [rule for rule in sorted(src.glob("*.mdc")) if rule.is_file()]
    _prune_orphaned_rule_links(dest_dir, src, {rule.stem for rule in rules})

    return [_symlink_rule(rule, dest_dir / (rule.stem + suffix)) for rule in rules]
