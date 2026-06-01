"""Vendor surface verification service.

Reproduces the behavior of agents/shared/verify-vendors.sh:
- Checks each vendor's surface paths (skills, subagents, MCP, hooks, etc.)
- path missing → VendorSurface(status="missing")
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

from dotfiles.core.fsutil import list_dir
from dotfiles.core.models import Vendor, VendorSurface


class VendorVerifyService:
    """Build the list of VendorSurface checks, mirroring verify-vendors.sh."""

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

    def vendors(self) -> list[VendorSurface]:
        results: list[VendorSurface] = []
        results.extend(self._claude_surfaces())
        results.extend(self._cursor_surfaces())
        results.extend(self._codex_surfaces())
        results.extend(self._gemini_surfaces())
        results.extend(self._pi_surfaces())
        return results

    # ------------------------------------------------------------------
    # Per-vendor helpers
    # ------------------------------------------------------------------

    def _claude_surfaces(self) -> list[VendorSurface]:
        h = self._home
        return [
            self._check("claude", "skills", h / ".claude" / "skills"),
            self._check("claude", "subagents", h / ".claude" / "agents"),
            self._check("claude", "rules", h / ".claude" / "rules"),
            self._check("claude", "MCP config", h / ".claude.json"),
            self._check("claude", "settings.json", h / ".claude" / "settings.json"),
            self._check("claude", "CLAUDE.md", h / ".claude" / "CLAUDE.md"),
        ]

    def _cursor_surfaces(self) -> list[VendorSurface]:
        h = self._home
        d = self._dotfiles_dir
        return [
            self._check("cursor", "skills (legacy)", h / ".cursor" / "skills"),
            self._check("cursor", "skills-cursor", h / ".cursor" / "skills-cursor"),
            self._check("cursor", "MCP config", h / ".cursor" / "mcp.json"),
            self._check("cursor", "rules (project)", d / "agents" / "cursor" / "rules"),
        ]

    def _codex_surfaces(self) -> list[VendorSurface]:
        h = self._home
        return [
            self._check("codex", "skills (vendor)", h / ".codex" / "skills"),
            self._check("codex", "skills (shared)", h / ".agents" / "skills"),
            self._check("codex", "subagents", h / ".codex" / "agents"),
            self._check("codex", "AGENTS.md", h / ".codex" / "AGENTS.md"),
            self._check("codex", "config.toml", h / ".codex" / "config.toml"),
            self._check("codex", "hooks.json", h / ".codex" / "hooks.json"),
            self._check("codex", "default.rules", h / ".codex" / "rules" / "default.rules"),
        ]

    def _gemini_surfaces(self) -> list[VendorSurface]:
        if not self._which("gemini"):
            return [
                VendorSurface(
                    vendor="gemini",
                    label="skipped",
                    status="skipped",
                    detail="gemini CLI not installed",
                )
            ]
        h = self._home
        return [
            self._check("gemini", "settings.json", h / ".gemini" / "settings.json"),
            self._check("gemini", "GEMINI.md", h / ".gemini" / "GEMINI.md"),
        ]

    def _pi_surfaces(self) -> list[VendorSurface]:
        if not self._which("pi"):
            return [
                VendorSurface(
                    vendor="pi", label="skipped", status="skipped", detail="pi CLI not installed"
                )
            ]
        h = self._home
        return [
            self._check("pi", "settings.json", h / ".pi" / "agent" / "settings.json"),
            self._check("pi", "models.json", h / ".pi" / "agent" / "models.json"),
            self._check("pi", "AGENTS.md", h / ".pi" / "agent" / "AGENTS.md"),
            self._check("pi", "subagents", h / ".pi" / "agent" / "agents"),
            self._check("pi", "skills (shared)", h / ".agents" / "skills"),
        ]

    # ------------------------------------------------------------------
    # Core path-check logic (mirrors check_path() in the shell script)
    # ------------------------------------------------------------------

    def _check(self, vendor: Vendor, label: str, path: Path) -> VendorSurface:
        if not path.exists():
            return VendorSurface(vendor=vendor, label=label, status="missing", detail=str(path))

        if path.is_dir():
            n_skills = self._count_skill_md(path)
            if n_skills > 0:
                return VendorSurface(
                    vendor=vendor,
                    label=label,
                    status="present",
                    detail=f"{n_skills} skills @ {path}",
                )
            # count all entries (ls -A equivalent)
            n_entries = len(list_dir(path))
            if n_entries > 0:
                return VendorSurface(
                    vendor=vendor,
                    label=label,
                    status="present",
                    detail=f"{n_entries} entries @ {path}",
                )
            # empty dir
            return VendorSurface(
                vendor=vendor, label=label, status="empty", detail=f"empty: {path}"
            )

        # plain file (or symlink that exists)
        return VendorSurface(vendor=vendor, label=label, status="present", detail=str(path))

    def _count_skill_md(self, path: Path) -> int:
        """Count SKILL.md files at maxdepth 2 (the dir itself + immediate subdirs)."""
        children = list_dir(path)
        direct = sum(1 for c in children if c.name == "SKILL.md")
        subdirs = [c for c in children if c.is_dir()]
        nested = sum(1 for sub in subdirs for gc in list_dir(sub) if gc.name == "SKILL.md")
        return direct + nested
