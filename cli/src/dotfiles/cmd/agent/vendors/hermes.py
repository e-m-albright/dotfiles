"""agent_setup.hermes — NousResearch ``hermes-agent`` (the ~/.hermes slot).

Hermes is a **skills** vendor for us, nothing more:
  - Symlink the canonical ``ai/skills`` library into ``~/.hermes/skills`` (single
    source of truth — edits in ai/skills reflect immediately), pruning stale copies.

What we deliberately do NOT deploy, and why (deploy = truth, no aspirational wiring):
  - rules: Hermes loads behavioural rules from project ``AGENTS.md``/``CLAUDE.md``/
    ``.cursorrules`` auto-injected from the CWD (hermes_cli/tips.py). The only global
    instruction slot is ``~/.hermes/SOUL.md`` — Hermes' own seeded *persona*, not ours
    to overwrite — so there is no global rules surface we own.
  - mcp / hooks / subagents: no documented global config schema we can write
    deterministically (MCP is a runtime registry; subagents are the ``delegate_task``
    tool; the hooks/ dir format is undocumented).

All paths are injected; Path.home() MUST NOT appear here.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.agent.lib import StepResult
from dotfiles.fsutil import prune_broken_symlinks, symlink


def setup_hermes(
    *,
    runner: ProcessRunner,
    home: Path,
    dotfiles_dir: Path,
    which: Callable[[str], str | None] = shutil.which,
) -> list[StepResult]:
    """Configure the ~/.hermes slot (NousResearch hermes-agent). Returns StepResults."""
    if which("hermes") is None:
        return [StepResult(level="success", message="skipped — hermes not installed")]

    hermes_home = home / ".hermes"
    hermes_home.mkdir(parents=True, exist_ok=True)
    return _setup_skills(dotfiles_dir, hermes_home)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _setup_skills(dotfiles_dir: Path, hermes_home: Path) -> list[StepResult]:
    """Symlink canonical skills into ``~/.hermes/skills`` (mirror, not append).

    Hermes reads global skills from ``~/.hermes/skills`` (hermes_cli/config.py).
    We replace any pre-existing copy of one of OUR skills with a fresh symlink so
    edits in ``ai/skills`` are picked up immediately, while leaving any
    externally-installed skill (a dir we don't own) untouched.
    """
    src = dotfiles_dir / "ai" / "skills"
    if not src.is_dir():
        return [StepResult(level="error", message="Skills source not found", details=str(src))]

    dest = hermes_home / "skills"
    dest.mkdir(parents=True, exist_ok=True)
    prune_broken_symlinks(dest)

    count = 0
    for skill_md in sorted(src.glob("*/SKILL.md")):
        link = dest / skill_md.parent.name
        # A prior `npx skills --copy` run leaves real directories here; replace
        # them with a symlink. symlink() handles existing links/files but not
        # populated dirs, so clear those first.
        if link.is_dir() and not link.is_symlink():
            shutil.rmtree(link)
        symlink(skill_md.parent, link)
        count += 1

    return [
        StepResult(level="success", message=f"Linked {count} skills (hermes → ~/.hermes/skills)")
    ]
