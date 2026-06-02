"""agent local — align a target repo's custom agent instructions to the standard.

Idempotent. Wires a project so one canonical rule source (``.ai/rules/*.mdc``)
reaches every agent that project uses:
  - generated into ``AGENTS.md`` for the harnesses that only read a root file
    (Claude Code, Codex, Gemini, Pi), between fenced markers
  - symlinked into ``.cursor/rules/`` for Cursor, which reads a rules dir natively

Applies by default; ``--check`` reports drift without touching the target.
``--vendors`` selects which tools the project supports (default: the canonical
set, same as ``agent global setup``). Replaces the old one-shot
``agent migrate-rules-sync``.

The actual rule generation lives in the deployed ``scripts/sync-agent-rules.sh``
engine (bash, because it also runs from the target repo's own pre-commit hook).
This module is the orchestrator: it deploys/updates that engine, ensures the
AGENTS.md markers exist, runs it, and prunes decorative dead rule symlinks.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.result import StepResult

# Marker pair must match scripts/sync-agent-rules.sh exactly, or the engine
# can't find the block it owns.
_BEGIN_MARKER = "<!-- BEGIN: project rules (auto-generated from .ai/rules/) -->"
_END_MARKER = "<!-- END: project rules -->"

# Harnesses that load only a root instructions file pretend to honour a project
# rules dir via these symlinks, but don't — so we prune them per in-scope vendor.
_DEAD_RULE_LINKS = {
    "claude": ".claude/rules",
    "codex": ".codex/rules",
    "gemini": ".gemini/rules",
}

# The canonical tool set, mirroring agent global setup's _AgentChoice.
CANONICAL_VENDORS = ("claude", "cursor", "codex", "gemini", "pi")


def align_repo(
    *,
    runner: ProcessRunner,
    dotfiles_dir: Path,
    target: Path,
    vendors: set[str],
    check: bool = False,
    force: bool = False,
    keep_dead_symlinks: bool = False,
) -> list[StepResult]:
    """Align *target* repo's agent instructions to the standard. Returns steps."""
    if not (target / ".git").is_dir():
        return [StepResult(level="error", message=f"{target} is not a git repository")]

    scaffold = dotfiles_dir / "ai" / "rules-sync"
    results: list[StepResult] = []
    results.extend(_deploy_engine(scaffold, target, check=check, force=force))
    results.extend(_deploy_lefthook(scaffold, target, check=check))

    markers = _ensure_markers(target, check=check)
    results.append(markers)
    if markers.level == "error":
        return results

    results.append(_run_engine(runner, target, vendors=vendors, check=check))
    if not keep_dead_symlinks:
        results.extend(_clean_dead_links(target, vendors=vendors, check=check))
    return results


def _deploy_engine(scaffold: Path, target: Path, *, check: bool, force: bool) -> list[StepResult]:
    """Copy scripts/sync-agent-rules.sh into the target (or report drift)."""
    src = scaffold / "scripts" / "sync-agent-rules.sh"
    dest = target / "scripts" / "sync-agent-rules.sh"
    current = dest.read_text() if dest.is_file() else None
    wanted = src.read_text()

    if current == wanted:
        return [StepResult(level="success", message="sync engine current")]
    if check:
        what = "out of date" if current is not None else "missing"
        return [StepResult(level="warn", message=f"drift: scripts/sync-agent-rules.sh {what}")]
    if current is not None and not force:
        return [
            StepResult(
                level="info",
                message="scripts/sync-agent-rules.sh exists (use --force to overwrite)",
            )
        ]

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dest)
    dest.chmod(0o755)
    return [StepResult(level="success", message="deployed scripts/sync-agent-rules.sh")]


def _deploy_lefthook(scaffold: Path, target: Path, *, check: bool) -> list[StepResult]:
    """Drop the lefthook drift-guard fragment unless it's already wired in."""
    lefthook = target / "lefthook.yml"
    if lefthook.is_file() and "agent-rules-synced" in lefthook.read_text():
        return [StepResult(level="success", message="lefthook drift guard already wired")]

    fragment = target / "lefthook.agent-rules.yml"
    if fragment.is_file():
        return [StepResult(level="info", message="lefthook.agent-rules.yml present — merge it in")]
    if check:
        return [StepResult(level="warn", message="drift: no lefthook drift guard for agent rules")]

    shutil.copy(scaffold / "lefthook.agent-rules.yml", fragment)
    return [
        StepResult(level="success", message="deployed lefthook.agent-rules.yml (merge into hooks)")
    ]


def _ensure_markers(target: Path, *, check: bool) -> StepResult:
    """Ensure AGENTS.md carries the fenced rules block markers."""
    agents_md = target / "AGENTS.md"
    if not agents_md.is_file():
        return StepResult(level="error", message="no AGENTS.md — create it, then re-run")
    if _BEGIN_MARKER in agents_md.read_text():
        return StepResult(level="success", message="AGENTS.md markers present")
    if check:
        return StepResult(level="warn", message="drift: AGENTS.md missing rules-block markers")

    with agents_md.open("a", encoding="utf-8") as fh:
        fh.write(f"\n---\n\n{_BEGIN_MARKER}\n{_END_MARKER}\n")
    return StepResult(level="success", message="added rules-block markers to AGENTS.md")


def _run_engine(
    runner: ProcessRunner, target: Path, *, vendors: set[str], check: bool
) -> StepResult:
    """Invoke the deployed engine to render rules (or verify they're current)."""
    script = target / "scripts" / "sync-agent-rules.sh"
    if not script.is_file():
        return StepResult(level="warn", message="engine not deployed — skipped rule render")

    cmd = [str(script)]
    if check:
        cmd.append("--check")
    if "cursor" not in vendors:
        cmd.append("--no-cursor")

    result = runner.run(tuple(cmd))
    if result.ok:
        verb = "current" if check else "rendered"
        return StepResult(level="success", message=f"project rules {verb}")
    detail = (result.stderr or result.stdout).strip()
    return StepResult(level="error", message="rule render failed", details=detail)


def _clean_dead_links(target: Path, *, vendors: set[str], check: bool) -> list[StepResult]:
    """Prune decorative dead rule symlinks for the in-scope root-file harnesses."""
    out: list[StepResult] = []
    for vendor, rel in _DEAD_RULE_LINKS.items():
        if vendor not in vendors:
            continue
        link = target / rel
        if not link.is_symlink():
            continue
        if check:
            out.append(StepResult(level="warn", message=f"drift: dead symlink {rel}"))
            continue
        link.unlink()
        out.append(StepResult(level="success", message=f"removed dead symlink {rel}"))
    return out
