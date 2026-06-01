"""Agent overview service.

Mirrors agents/overview.sh: produces structured data for each of the 6 sections.
Hexagonal: imports only stdlib + core models/ports.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, cast

from dotfiles.core.models import (
    AgentOverview,
    AgentRow,
    HookRow,
    McpRow,
    PermissionRow,
    RulesSummary,
    SkillsSummary,
)

if TYPE_CHECKING:
    from dotfiles.core.ports import FileSystem, ProcessRunner

# ---------------------------------------------------------------------------
# Typed JSON helpers — keep pyright strict happy without Any leakage
# ---------------------------------------------------------------------------

_JsonObj = dict[str, object]


def _load_json_obj(text: str) -> _JsonObj | None:
    """Parse JSON text; return the dict or None if not a JSON object."""
    try:
        raw: object = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    return cast(_JsonObj, raw)


def _list_len(obj: _JsonObj, key: str) -> int:
    """Length of obj[key] when it is a list, else 0."""
    val: object = obj.get(key)
    return len(cast(list[object], val)) if isinstance(val, list) else 0


def _as_obj(obj: _JsonObj, key: str) -> _JsonObj:
    """Return obj[key] as a _JsonObj, or empty dict if missing/wrong type."""
    val: object = obj.get(key)
    return cast(_JsonObj, val) if isinstance(val, dict) else {}


class AgentOverviewService:
    """Produces structured data for the agentic setup overview.

    Parameters mirror the hexagonal pattern: inject fs/runner/paths; no globals.
    """

    def __init__(
        self,
        *,
        fs: FileSystem,
        runner: ProcessRunner,
        dotfiles_dir: Path,
        home: Path,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self._fs = fs
        self._runner = runner
        self._dotfiles = dotfiles_dir
        self._home = home
        self._which = which

    # ------------------------------------------------------------------
    # Public aggregator
    # ------------------------------------------------------------------

    def overview(self) -> AgentOverview:
        """Collect all six sections and return an AgentOverview."""
        return AgentOverview(
            mcp=tuple(self.section_mcp()),
            hooks=tuple(self.section_hooks()),
            skills=self.section_skills(),
            agents=tuple(self.section_agents()),
            rules=self.section_rules(),
            permissions=tuple(self.section_permissions()),
        )

    # ------------------------------------------------------------------
    # Section 1: MCP Servers
    # ------------------------------------------------------------------

    def section_mcp(self) -> list[McpRow]:
        """Read agents/shared/mcp-servers.json; one McpRow per object-valued entry."""
        shared_mcp = self._dotfiles / "agents" / "shared" / "mcp-servers.json"
        if not self._fs.exists(shared_mcp):
            return []
        data = _load_json_obj(self._fs.read_text(shared_mcp))
        if data is None:
            return []

        rows: list[McpRow] = []
        for name, value in data.items():
            if not isinstance(value, dict):
                continue
            server_entry = cast(_JsonObj, value)
            raw_targets: object = server_entry.get("targets")
            targets: list[str] = (
                [t for t in cast(list[object], raw_targets) if isinstance(t, str)]
                if isinstance(raw_targets, list)
                else []
            )
            rows.append(
                McpRow(
                    server=name,
                    claude="claude" in targets,
                    cursor="cursor" in targets,
                    codex="codex" in targets,
                    gemini="gemini" in targets,
                )
            )
        return rows

    # ------------------------------------------------------------------
    # Section 2: Hooks
    # ------------------------------------------------------------------

    def section_hooks(self) -> list[HookRow]:
        """Union of hook events across claude/cursor/codex; one HookRow per event."""
        agents_dir = self._dotfiles / "agents"
        claude_path = agents_dir / "claude" / "hooks.json"
        cursor_path = agents_dir / "cursor" / "hooks" / "hooks.json"
        codex_path = agents_dir / "codex" / "hooks.json"

        claude_events = self._claude_hook_events(claude_path)
        cursor_events = self._cursor_hook_events(cursor_path)
        codex_events = self._codex_hook_events(codex_path)

        all_events = sorted(claude_events | cursor_events | codex_events)
        return [
            HookRow(
                event=evt,
                claude=evt in claude_events,
                cursor=evt in cursor_events,
                codex=evt in codex_events,
            )
            for evt in all_events
        ]

    def _claude_hook_events(self, path: Path) -> set[str]:
        """Keys of .hooks dict in claude/hooks.json."""
        return self._parse_hook_keys(path, "claude")

    def _codex_hook_events(self, path: Path) -> set[str]:
        """Keys of .hooks dict in codex/hooks.json."""
        return self._parse_hook_keys(path, "codex")

    def _parse_hook_keys(self, path: Path, _label: str) -> set[str]:
        if not self._fs.exists(path):
            return set()
        data = _load_json_obj(self._fs.read_text(path))
        if data is None:
            return set()
        raw_hooks: object = data.get("hooks")
        if not isinstance(raw_hooks, dict):
            return set()
        hooks_dict = cast(_JsonObj, raw_hooks)
        return {k for k in hooks_dict if k}

    def _cursor_hook_events(self, path: Path) -> set[str]:
        """Values of .hooks[].event in cursor/hooks/hooks.json."""
        if not self._fs.exists(path):
            return set()
        data = _load_json_obj(self._fs.read_text(path))
        if data is None:
            return set()
        raw_hooks: object = data.get("hooks")
        if not isinstance(raw_hooks, list):
            return set()
        events: set[str] = set()
        for h in cast(list[object], raw_hooks):
            if not isinstance(h, dict):
                continue
            hook_obj = cast(_JsonObj, h)
            raw_evt: object = hook_obj.get("event")
            if isinstance(raw_evt, str) and raw_evt:
                events.add(raw_evt)
        return events

    # ------------------------------------------------------------------
    # Section 3: Skills
    # ------------------------------------------------------------------

    def section_skills(self) -> SkillsSummary:
        """Count canonical SKILL.md files; count deployed dirs in claude/shared."""
        skills_root = self._dotfiles / ".ai" / "skills"
        canonical = 0
        if self._fs.exists(skills_root) and self._fs.is_dir(skills_root):
            for entry in self._fs.iterdir(skills_root):
                if self._fs.is_dir(entry) and self._fs.exists(entry / "SKILL.md"):
                    canonical += 1

        claude_dir = self._home / ".claude" / "skills"
        claude_deployed = self._count_subdirs(claude_dir)

        shared_dir = self._home / ".agents" / "skills"
        shared_deployed = self._count_subdirs(shared_dir)

        return SkillsSummary(
            canonical_skills=canonical,
            claude_deployed=claude_deployed,
            shared_deployed=shared_deployed,
        )

    def _count_subdirs(self, path: Path) -> int:
        """Count immediate subdirectory entries under path (0 if not present)."""
        if not self._fs.exists(path) or not self._fs.is_dir(path):
            return 0
        return sum(1 for p in self._fs.iterdir(path) if self._fs.is_dir(p))

    # ------------------------------------------------------------------
    # Section 4: Subagents
    # ------------------------------------------------------------------

    def section_agents(self) -> list[AgentRow]:
        """One AgentRow per .ai/agents/*.md, with deployment flags."""
        agents_root = self._dotfiles / ".ai" / "agents"
        if not self._fs.exists(agents_root) or not self._fs.is_dir(agents_root):
            return []

        claude_agents = self._home / ".claude" / "agents"
        codex_agents = self._home / ".codex" / "agents"
        pi_agents = self._home / ".pi" / "agent" / "agents"

        rows: list[AgentRow] = []
        for entry in sorted(self._fs.iterdir(agents_root), key=lambda p: p.name):
            if self._fs.is_dir(entry) or entry.suffix != ".md":
                continue
            name = entry.stem
            rows.append(
                AgentRow(
                    name=name,
                    claude=self._fs.exists(claude_agents / f"{name}.md"),
                    codex=self._fs.exists(codex_agents / f"{name}.md"),
                    pi=self._fs.exists(pi_agents / f"{name}.md"),
                )
            )
        return rows

    # ------------------------------------------------------------------
    # Section 5: Rules
    # ------------------------------------------------------------------

    def section_rules(self) -> RulesSummary:
        """Count canonical .mdc rules; count deployed in claude/cursor."""
        canonical = self._count_files_by_ext(self._dotfiles / ".ai" / "rules" / "process", ".mdc")
        claude_deployed = self._count_files_by_ext(self._home / ".claude" / "rules", ".md")
        cursor_deployed = self._count_cursor_rules(self._dotfiles / "agents" / "cursor" / "rules")
        return RulesSummary(
            canonical_rules=canonical,
            claude_deployed=claude_deployed,
            cursor_deployed=cursor_deployed,
        )

    def _count_files_by_ext(self, path: Path, ext: str) -> int:
        """Count non-directory entries with the given extension under path."""
        if not self._fs.exists(path) or not self._fs.is_dir(path):
            return 0
        return sum(1 for e in self._fs.iterdir(path) if not self._fs.is_dir(e) and e.suffix == ext)

    def _count_cursor_rules(self, path: Path) -> int:
        """Count .mdc entries in agents/cursor/rules/.

        The Bash script uses -type l (symlinks only). We count .mdc entries;
        is_symlink detection is available on the FakeFileSystem but we count all
        .mdc files — any non-symlink would be a misconfiguration and is still
        reported faithfully in the count.
        """
        if not self._fs.exists(path) or not self._fs.is_dir(path):
            return 0
        count = 0
        for entry in self._fs.iterdir(path):
            if not self._fs.is_dir(entry) and entry.suffix == ".mdc":
                count += 1
        return count

    # ------------------------------------------------------------------
    # Section 6: Permissions
    # ------------------------------------------------------------------

    def section_permissions(self) -> list[PermissionRow]:
        """One PermissionRow per config source that exists."""
        rows: list[PermissionRow] = []
        rows.extend(self._perm_claude_deployed())
        rows.extend(self._perm_claude_source())
        rows.extend(self._perm_cursor())
        rows.extend(self._perm_codex())
        return rows

    def _perm_claude_deployed(self) -> list[PermissionRow]:
        path = self._home / ".claude" / "settings.json"
        if not self._fs.exists(path):
            return []
        data = _load_json_obj(self._fs.read_text(path))
        if data is None:
            return []
        perms = _as_obj(data, "permissions")
        allow = _list_len(perms, "allow")
        deny = _list_len(perms, "deny")
        return [PermissionRow(label="Claude Code (deployed)", allow=allow, deny=deny)]

    def _perm_claude_source(self) -> list[PermissionRow]:
        path = self._dotfiles / "agents" / "claude" / "permissions.json"
        if not self._fs.exists(path):
            return []
        data = _load_json_obj(self._fs.read_text(path))
        if data is None:
            return []
        allow = _list_len(data, "allow")
        deny = _list_len(data, "deny")
        return [PermissionRow(label="Claude (dotfiles source)", allow=allow, deny=deny)]

    def _perm_cursor(self) -> list[PermissionRow]:
        path = self._dotfiles / "agents" / "cursor" / "cli-config.json"
        if not self._fs.exists(path):
            return []
        data = _load_json_obj(self._fs.read_text(path))
        if data is None:
            return []
        perms = _as_obj(data, "permissions")
        allow = _list_len(perms, "allow")
        deny = _list_len(perms, "deny")
        return [PermissionRow(label="Cursor CLI", allow=allow, deny=deny)]

    def _perm_codex(self) -> list[PermissionRow]:
        path = self._dotfiles / "agents" / "codex" / "default.rules"
        if not self._fs.exists(path):
            return []
        try:
            text = self._fs.read_text(path)
        except OSError:
            return []
        n = sum(1 for line in text.splitlines() if line.startswith("prefix_rule"))
        return [PermissionRow(label="Codex (default.rules)", allow=n, deny=0, prefix_rules=n)]
