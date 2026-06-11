"""Agent surface verification service.

Reproduces the behavior of agents/shared/verify-vendors.sh:
- Checks each agent's surface paths (skills, subagents, MCP, hooks, etc.)
- path missing → AgentSurface(status="missing")
- dir with SKILL.md files (maxdepth 2) → status="present", detail="N skills @ path"
- dir with other entries → status="present", detail="N entries @ path"
- empty dir → status="empty", detail="empty: path"
- file → status="present", detail=str(path)
- Gemini/Pi sections gated on their CLI being present; else status="skipped"

Exit 0 always (informational).
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from dotfiles.agent import AGENTS, SURFACE_PATHS, Agent
from dotfiles.cmd.agent.models import AgentSurface
from dotfiles.fsutil import list_dir

# The uniform checklist shown for every agent: (display label, registry surface key).
# "rules" reads the deployed kernel file (CLAUDE.md / AGENTS.md / .mdc) — the same text
# every vendor loads — not a separate dir; there is no longer a redundant
# "instructions" row, and cursor (.mdc) + hermes (runtime) are handled in _rules_surface.
_ATTRIBUTES: tuple[tuple[str, str], ...] = (
    ("skills", "skills"),
    ("subagents", "subagents"),
    ("rules", "instructions"),
    ("mcp", "mcp"),
    ("hooks", "hooks"),
    ("settings", "settings"),
)


class AgentVerifyService:
    """Build the list of AgentSurface checks, mirroring verify-vendors.sh."""

    def __init__(
        self,
        *,
        home: Path,
        dotfiles_dir: Path,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self._home = home
        self._dotfiles_dir = dotfiles_dir
        self._which = which

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def vendors(self) -> list[AgentSurface]:
        """A uniform attribute checklist for every agent — same rows in the same order.

        Each (agent, attribute) resolves to present / missing / empty, or n/a
        (``skipped``) where the agent has no such surface — so you can read down
        any agent and see exactly what it has and what it lacks.
        """
        results: list[AgentSurface] = []
        for agent in AGENTS:
            for label, key in _ATTRIBUTES:
                if label == "rules":
                    results.append(self._rules_surface(agent))
                else:
                    results.append(self._surface(agent, label, SURFACE_PATHS[key].get(agent)))
        return results

    def _surface(self, agent: Agent, label: str, rel: str | None) -> AgentSurface:
        """One uniform row: n/a when *rel* is None, else the path-existence check."""
        if rel is None:
            return AgentSurface(agent=agent, label=label, status="skipped", quantity="n/a")
        return self._check(agent, label, self._home / rel)

    def _rules_surface(self, agent: Agent) -> AgentSurface:
        """The deployed kernel/rules — the instructions file every vendor loads.

        Mirrors uniformity's `_deploy_rules`, so the vendor page and uniformity can't
        disagree: claude/codex/gemini/pi carry it in CLAUDE.md/AGENTS.md; cursor in its
        generated `.mdc`; hermes injects a project AGENTS.md at runtime (no global file
        we own). Every vendor does rules — none should read "n/a" for an unused dir.
        """
        if agent == "cursor":
            mdc_dir = self._dotfiles_dir / "ai" / "agents" / "cursor" / "rules"
            has_mdc = mdc_dir.is_dir() and any(p.suffix == ".mdc" for p in list_dir(mdc_dir))
            return AgentSurface(
                agent=agent,
                label="rules",
                status="present" if has_mdc else "missing",
                quantity=".mdc",
                detail=str(mdc_dir),
            )
        if agent == "hermes":
            return AgentSurface(
                agent=agent, label="rules", status="skipped", quantity="runtime (project AGENTS.md)"
            )
        return self._surface(agent, "rules", SURFACE_PATHS["instructions"].get(agent))

    # ------------------------------------------------------------------
    # Core path-check logic (mirrors check_path() in the shell script)
    # ------------------------------------------------------------------

    def _check(self, agent: Agent, label: str, path: Path) -> AgentSurface:
        if not path.exists():
            return AgentSurface(
                agent=agent, label=label, status="missing", detail=str(path), path=str(path)
            )

        if path.is_dir():
            n_skills = self._count_skill_md(path)
            if n_skills > 0:
                return AgentSurface(
                    agent=agent,
                    label=label,
                    status="present",
                    detail=f"{n_skills} skills @ {path}",
                    quantity=f"{n_skills} skills",
                    path=str(path),
                )
            # count only entries that resolve — a dir of dangling symlinks
            # (e.g. orphaned ~/.claude/rules links) is not a healthy surface.
            n_entries = sum(1 for e in list_dir(path) if e.exists())
            if n_entries > 0:
                return AgentSurface(
                    agent=agent,
                    label=label,
                    status="present",
                    detail=f"{n_entries} entries @ {path}",
                    quantity=f"{n_entries} entries",
                    path=str(path),
                )
            # empty dir
            return AgentSurface(
                agent=agent,
                label=label,
                status="empty",
                detail=f"empty: {path}",
                quantity="empty",
                path=str(path),
            )

        # plain file (or symlink that exists)
        return AgentSurface(
            agent=agent, label=label, status="present", detail=str(path), path=str(path)
        )

    def _count_skill_md(self, path: Path) -> int:
        """Count SKILL.md files at maxdepth 2 (the dir itself + immediate subdirs)."""
        children = list_dir(path)
        direct = sum(1 for c in children if c.name == "SKILL.md")
        subdirs = [c for c in children if c.is_dir()]
        nested = sum(1 for sub in subdirs for gc in list_dir(sub) if gc.name == "SKILL.md")
        return direct + nested
