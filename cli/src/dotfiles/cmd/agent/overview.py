"""Agent overview service.

Produces structured data for each of the 6 sections:
MCP, hooks, skills, agents, rules, permissions.
Hexagonal: imports only stdlib + pydantic + core models/ports.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from dotfiles.cmd.agent.capability_matrix import (
    CapabilityRow,
    capability_rows,
    fleet_doc_stale_days,
)
from dotfiles.cmd.agent.config import (
    ClaudeHooksConfig,
    CursorHooksConfig,
    PermissionsBlock,
    SettingsWithPermissions,
    load_config,
)
from dotfiles.cmd.agent.models import (
    AgentOverview,
    AgentSurface,
    HookRow,
    McpRow,
    PermissionRow,
    PluginRow,
    RulesSummary,
    SkillsSummary,
    SubagentRow,
    ValueRow,
)
from dotfiles.cmd.agent.vendors.claude import parse_plugins_yaml
from dotfiles.cmd.agent.verify import AgentVerifyService
from dotfiles.fsutil import list_dir

if TYPE_CHECKING:
    from dotfiles.adapters.ports import ProcessRunner


class _McpServersFile(BaseModel):
    """Just the ``mcpServers`` map of an agent's MCP config (extra keys ignored)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    mcp_servers: dict[str, object] = Field(default_factory=dict, alias="mcpServers")


class AgentOverviewService:
    """Produces structured data for the agentic setup overview.

    Parameters mirror the hexagonal pattern: inject runner/paths; no globals.
    """

    def __init__(
        self,
        *,
        runner: ProcessRunner,
        dotfiles_dir: Path,
        home: Path,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
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
            vendor_surfaces=tuple(self.vendor_surfaces()),
            plugins=tuple(self.section_plugins()),
            skills_rules=tuple(self.section_skills_rules()),
            capabilities=tuple(self.section_capabilities()),
            fleet_doc_stale_days=fleet_doc_stale_days(self._dotfiles, date.today()),
        )

    def section_capabilities(self) -> list[CapabilityRow]:
        """The cross-vendor capability matrix (vendor support + provenance)."""
        return capability_rows()

    # ------------------------------------------------------------------
    # Skills & Rules (colocated value matrix: per-agent deployment)
    # ------------------------------------------------------------------

    def section_skills_rules(self) -> list[ValueRow]:
        """Per-agent skill counts and where each vendor's rules live (files vs embedded)."""
        h = self._home
        skills = {
            "claude": str(self._count_subdirs(h / ".claude" / "skills")),
            "cursor": str(self._count_subdirs(h / ".cursor" / "skills-cursor")),
            "codex": str(self._count_subdirs(h / ".agents" / "skills")),
            "gemini": "—",  # Gemini has no skills surface
            "pi": str(self._count_subdirs(h / ".agents" / "skills")),
        }
        # Only Claude/Cursor read a rules directory (cell = file count); the rest
        # carry rules embedded in their single instruction file (cell = its name).
        rules = {
            "claude": str(self._count_files_by_ext(h / ".claude" / "rules", ".md")),
            "cursor": str(self._count_cursor_rules(self._cursor_rules_dir())),
            "codex": "AGENTS" if (h / ".codex" / "AGENTS.md").exists() else "—",
            "gemini": "AGENTS" if (h / ".gemini" / "AGENTS.md").exists() else "—",
            "pi": "AGENTS" if (h / ".pi" / "agent" / "AGENTS.md").exists() else "—",
        }
        return [
            ValueRow(label="skills", cells=skills),
            ValueRow(label="rules", cells=rules),
        ]

    def _cursor_rules_dir(self) -> Path:
        return self._dotfiles / "ai" / "agents" / "cursor" / "rules"

    # ------------------------------------------------------------------
    # Agent surfaces (delegates to AgentVerifyService)
    # ------------------------------------------------------------------

    def vendor_surfaces(self) -> list[AgentSurface]:
        """Return agent surface presence checks, delegating to AgentVerifyService."""
        svc = AgentVerifyService(
            home=self._home,
            dotfiles_dir=self._dotfiles,
            which=self._which,
        )
        return svc.vendors()

    # ------------------------------------------------------------------
    # Section 1: MCP Servers
    # ------------------------------------------------------------------

    def section_mcp(self) -> list[McpRow]:
        """One McpRow per server, from each agent's LIVE config (codex via `codex mcp list`)."""
        live = self._live_mcp()
        names = sorted({name for servers in live.values() for name in servers})
        return [
            McpRow(
                server=name,
                claude=name in live["claude"],
                cursor=name in live["cursor"],
                codex=name in live["codex"],
                gemini=name in live["gemini"],
                pi=False,  # Pi has no MCP surface (rendered n/a, not a failure)
            )
            for name in names
        ]

    def _live_mcp(self) -> dict[str, set[str]]:
        """Server names actually configured per agent, read from live state."""
        h = self._home
        return {
            "claude": self._mcp_config_servers(h / ".claude.json"),
            "cursor": self._mcp_config_servers(h / ".cursor" / "mcp.json"),
            "gemini": self._mcp_config_servers(h / ".gemini" / "settings.json"),
            "codex": self._codex_mcp(),
            "pi": set(),
        }

    def _mcp_config_servers(self, path: Path) -> set[str]:
        """The ``mcpServers`` keys in an agent's MCP config (empty if absent/invalid)."""
        cfg = load_config(path, _McpServersFile)
        return set(cfg.mcp_servers) if cfg is not None else set()

    def _codex_mcp(self) -> set[str]:
        """Live Codex MCP servers via `codex mcp list` (the name is the first token)."""
        result = self._runner.run(("codex", "mcp", "list"))
        if not result.ok:
            return set()
        servers: set[str] = set()
        for line in result.stdout.splitlines():
            if ("enabled" in line or "disabled" in line) and (parts := line.split()):
                servers.add(parts[0])
        return servers

    # ------------------------------------------------------------------
    # Plugins (Claude Code marketplace)
    # ------------------------------------------------------------------

    def section_plugins(self) -> list[PluginRow]:
        """Installed Claude Code plugins, flagged against the plugins.yaml allowlist."""
        config = self._home / ".claude" / "plugins" / "installed_plugins.json"
        if not config.is_file():
            return []
        try:
            data = json.loads(config.read_text())
        except (OSError, json.JSONDecodeError):
            return []
        declared = self._declared_plugin_names()
        rows: list[PluginRow] = []
        for ref, installs in data.get("plugins", {}).items():
            name, _, marketplace = str(ref).partition("@")
            version = installs[0].get("version", "") if installs else ""
            rows.append(
                PluginRow(
                    name=name,
                    marketplace=marketplace,
                    version=version,
                    declared=name in declared,
                )
            )
        return sorted(rows, key=lambda r: r.name)

    def _declared_plugin_names(self) -> set[str]:
        """Bare plugin names declared in plugins.yaml (our allowlist; '' if absent)."""
        src = self._dotfiles / "ai" / "agents" / "claude" / "plugins.yaml"
        if not src.is_file():
            return set()
        return {key.split("@", 1)[0] for key in parse_plugins_yaml(src)}

    # ------------------------------------------------------------------
    # Section 2: Hooks
    # ------------------------------------------------------------------

    def section_hooks(self) -> list[HookRow]:
        """Union of hook events across claude/cursor/codex; one HookRow per event."""
        agents_dir = self._dotfiles / "ai" / "agents"
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
        cfg = load_config(path, ClaudeHooksConfig)
        if cfg is None:
            return set()
        return {k for k in cfg.hooks if k}

    def _codex_hook_events(self, path: Path) -> set[str]:
        """Keys of .hooks dict in codex/hooks.json."""
        cfg = load_config(path, ClaudeHooksConfig)
        if cfg is None:
            return set()
        return {k for k in cfg.hooks if k}

    def _cursor_hook_events(self, path: Path) -> set[str]:
        """Values of .hooks[].event in cursor/hooks/hooks.json."""
        cfg = load_config(path, CursorHooksConfig)
        if cfg is None:
            return set()
        return {h.event for h in cfg.hooks if h.event}

    # ------------------------------------------------------------------
    # Section 3: Skills
    # ------------------------------------------------------------------

    def section_skills(self) -> SkillsSummary:
        """Count canonical SKILL.md files; count deployed dirs in claude/shared."""
        skills_root = self._dotfiles / "ai" / "skills"
        canonical = 0
        if skills_root.exists() and skills_root.is_dir():
            for entry in list_dir(skills_root):
                if entry.is_dir() and (entry / "SKILL.md").exists():
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
        if not path.exists() or not path.is_dir():
            return 0
        return sum(1 for p in list_dir(path) if p.is_dir())

    # ------------------------------------------------------------------
    # Section 4: Subagents
    # ------------------------------------------------------------------

    def section_agents(self) -> list[SubagentRow]:
        """One SubagentRow per .ai/agents/*.md, with deployment flags."""
        agents_root = self._dotfiles / "ai" / "subagents"
        if not agents_root.exists() or not agents_root.is_dir():
            return []

        claude_agents = self._home / ".claude" / "agents"
        codex_agents = self._home / ".codex" / "agents"
        pi_agents = self._home / ".pi" / "agent" / "agents"

        rows: list[SubagentRow] = []
        for entry in list_dir(agents_root):
            if entry.is_dir() or entry.suffix != ".md":
                continue
            name = entry.stem
            rows.append(
                SubagentRow(
                    name=name,
                    claude=(claude_agents / f"{name}.md").exists(),
                    codex=(codex_agents / f"{name}.md").exists(),
                    pi=(pi_agents / f"{name}.md").exists(),
                )
            )
        return rows

    # ------------------------------------------------------------------
    # Section 5: Rules
    # ------------------------------------------------------------------

    def section_rules(self) -> RulesSummary:
        """Count canonical .mdc rules; count deployed in claude/cursor."""
        canonical = self._count_files_by_ext(self._dotfiles / "ai" / "rules" / "process", ".mdc")
        claude_deployed = self._count_files_by_ext(self._home / ".claude" / "rules", ".md")
        cursor_deployed = self._count_cursor_rules(
            self._dotfiles / "ai" / "agents" / "cursor" / "rules"
        )
        return RulesSummary(
            canonical_rules=canonical,
            claude_deployed=claude_deployed,
            cursor_deployed=cursor_deployed,
        )

    def _count_files_by_ext(self, path: Path, ext: str) -> int:
        """Count non-directory entries with the given extension under path."""
        if not path.exists() or not path.is_dir():
            return 0
        return sum(1 for e in list_dir(path) if not e.is_dir() and e.suffix == ext)

    def _count_cursor_rules(self, path: Path) -> int:
        """Count .mdc entries in agents/cursor/rules/."""
        if not path.exists() or not path.is_dir():
            return 0
        count = 0
        for entry in list_dir(path):
            if not entry.is_dir() and entry.suffix == ".mdc":
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
        cfg = load_config(path, SettingsWithPermissions)
        if cfg is None:
            return []
        return [
            PermissionRow(
                label="Claude Code (deployed)",
                allow=len(cfg.permissions.allow),
                deny=len(cfg.permissions.deny),
                source_path=str(path),
            )
        ]

    def _perm_claude_source(self) -> list[PermissionRow]:
        path = self._dotfiles / "ai" / "agents" / "claude" / "permissions.json"
        cfg = load_config(path, PermissionsBlock)
        if cfg is None:
            return []
        return [
            PermissionRow(
                label="Claude (dotfiles source)",
                allow=len(cfg.allow),
                deny=len(cfg.deny),
                source_path=str(path),
            )
        ]

    def _perm_cursor(self) -> list[PermissionRow]:
        path = self._dotfiles / "ai" / "agents" / "cursor" / "cli-config.json"
        cfg = load_config(path, SettingsWithPermissions)
        if cfg is None:
            return []
        return [
            PermissionRow(
                label="Cursor CLI",
                allow=len(cfg.permissions.allow),
                deny=len(cfg.permissions.deny),
                source_path=str(path),
            )
        ]

    def _perm_codex(self) -> list[PermissionRow]:
        path = self._dotfiles / "ai" / "agents" / "codex" / "default.rules"
        if not path.exists():
            return []
        try:
            text = path.read_text()
        except OSError:
            return []
        n = sum(1 for line in text.splitlines() if line.startswith("prefix_rule"))
        return [
            PermissionRow(
                label="Codex (default.rules)",
                allow=0,
                deny=0,
                prefix_rules=n,
                source_path=str(path),
            )
        ]
