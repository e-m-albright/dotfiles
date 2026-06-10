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

from dotfiles.agent import AGENTS, Agent
from dotfiles.cmd.agent.models import AgentSurface
from dotfiles.fsutil import list_dir

# The uniform attribute checklist shown for every agent, in order.
_ATTRIBUTES: tuple[str, ...] = (
    "skills",
    "subagents",
    "rules",
    "mcp",
    "hooks",
    "instructions",
    "settings",
)

# attribute -> {agent: $HOME-relative path, or None when the agent has no such
# surface (rendered n/a)}. Symlinked configs (cursor mcp/settings, pi settings)
# resolve through, so existence checks still pass.
_SURFACE_MAP: dict[str, dict[Agent, str | None]] = {
    "skills": {
        "claude": ".claude/skills",
        "cursor": ".cursor/skills",
        "codex": ".agents/skills",
        "gemini": None,
        "pi": ".agents/skills",
    },
    "subagents": {
        "claude": ".claude/agents",
        "cursor": None,
        "codex": ".codex/agents",
        "gemini": None,
        "pi": ".pi/agent/agents",
    },
    "rules": {  # only Claude reads a rules dir; the rest embed rules in instructions
        "claude": ".claude/rules",
        "cursor": None,
        "codex": None,
        "gemini": None,
        "pi": None,
    },
    "mcp": {
        "claude": ".claude.json",
        "cursor": ".cursor/mcp.json",
        "codex": ".codex/config.toml",
        "gemini": ".gemini/settings.json",
        "pi": None,
    },
    "hooks": {
        "claude": ".claude/settings.json",
        "cursor": None,
        "codex": ".codex/hooks.json",
        "gemini": None,
        "pi": None,
    },
    "instructions": {
        "claude": ".claude/CLAUDE.md",
        "cursor": None,
        "codex": ".codex/AGENTS.md",
        "gemini": ".gemini/AGENTS.md",
        "pi": ".pi/agent/AGENTS.md",
    },
    "settings": {
        "claude": ".claude/settings.json",
        "cursor": ".cursor/cli-config.json",
        "codex": ".codex/config.toml",
        "gemini": ".gemini/settings.json",
        "pi": ".pi/agent/settings.json",
    },
}


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
            for attribute in _ATTRIBUTES:
                rel = _SURFACE_MAP[attribute].get(agent)
                results.append(self._surface(agent, attribute, rel))
        return results

    def _surface(self, agent: Agent, label: str, rel: str | None) -> AgentSurface:
        """One uniform row: n/a when *rel* is None, else the path-existence check."""
        if rel is None:
            return AgentSurface(agent=agent, label=label, status="skipped", quantity="n/a")
        return self._check(agent, label, self._home / rel)

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
