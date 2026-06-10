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

from dotfiles.agent import AGENTS
from dotfiles.cmd.agent.capability_matrix import (
    CAPABILITY_MATRIX,
    CapabilityRow,
    capability_rows,
    fleet_doc_stale_days,
)
from dotfiles.cmd.agent.config import (
    PermissionsBlock,
    SettingsWithPermissions,
    load_config,
)
from dotfiles.cmd.agent.models import (
    AgentOverview,
    AgentSurface,
    CoverageState,
    HookRow,
    McpRow,
    PermissionRow,
    PluginRow,
    RulesSummary,
    SkillsSummary,
    SubagentRow,
    UniformityRow,
    ValueRow,
)
from dotfiles.cmd.agent.vendors.claude import parse_plugins_yaml
from dotfiles.cmd.agent.verify import AgentVerifyService
from dotfiles.fsutil import list_dir

if TYPE_CHECKING:
    from dotfiles.adapters.ports import ProcessRunner


# The uniform hook contract: each intent maps to the shared script every
# hook-capable vendor wires. Presence is proven by the basename appearing in a
# vendor's hooks config (so the matrix compares intents, not raw event names).
_HOOK_INTENTS: tuple[tuple[str, str], ...] = (
    ("guard-file", "guard-sensitive-file.sh"),
    ("guard-shell", "guard-destructive-shell.sh"),
    ("format", "format-on-save.sh"),
    ("notify", "notify.sh"),
)

# Capabilities we hold every vendor to a uniform standard on (the rest are
# tracked but not enforced). Each name must be a key in the capability matrix.
_ENFORCED_TIER: tuple[str, ...] = (
    "rules",
    "skills",
    "subagents",
    "statusline",
    "permissions",
    "hooks",
)


# (capability, vendor) pairs that the vendor supports but ONLY at a scope we can't
# reach with a global deploy — workspace-local config, an extension, or a beta with
# no stable API. These render as a not-globally-closable gap, not a red action item.
_LOCAL_ONLY: frozenset[tuple[str, str]] = frozenset(
    {
        ("subagents", "gemini"),  # agy: workspace .agents/ agent-scripts, no global dir
        ("hooks", "gemini"),  # agy: hook registration is workspace-local
        ("hooks", "pi"),  # pi: hooks come from the safe-git extension, not a global set
        ("statusline", "cursor"),  # cursor: statusline is beta, no stable deploy mechanism
    }
)


def _coverage(capability: str, agent: str, supported: bool, deployed: bool) -> CoverageState:
    """Classify one (capability, vendor) cell: na / active / local / gap."""
    if not supported:
        return "na"
    if deployed:
        return "active"
    return "local" if (capability, agent) in _LOCAL_ONLY else "gap"


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
            uniformity=tuple(self.section_uniformity()),
            fleet_doc_stale_days=fleet_doc_stale_days(self._dotfiles, date.today()),
        )

    def section_capabilities(self) -> list[CapabilityRow]:
        """The cross-vendor capability matrix (vendor support + provenance)."""
        return capability_rows()

    def section_uniformity(self) -> list[UniformityRow]:
        """Per-vendor coverage of the enforced tier: support (matrix) vs deployment.

        active = the vendor supports it AND we've deployed it; gap = supported but
        not yet deployed (a closable gap); na = the vendor doesn't support it.
        """
        support = {cap.key: cap.cells for cap in CAPABILITY_MATRIX}
        deployed = self._deployment_state()
        return [
            UniformityRow(
                capability=cap,
                cells={
                    agent: _coverage(
                        cap,
                        agent,
                        support[cap][agent].status in ("yes", "beta", "ext"),
                        deployed[agent].get(cap, False),
                    )
                    for agent in AGENTS
                },
            )
            for cap in _ENFORCED_TIER
        ]

    def _deployment_state(self) -> dict[str, dict[str, bool]]:
        """For each vendor, whether OUR deployment of each enforced capability is live.

        Pure path/config probes against $HOME — nothing asserted, everything checked.
        """
        per_cap = {
            "rules": self._deploy_rules(),
            "skills": self._deploy_skills(),
            "subagents": self._deploy_subagents(),
            "statusline": self._deploy_statusline(),
            "permissions": self._deploy_permissions(),
            "hooks": self._deploy_hooks(),
        }
        return {agent: {cap: states[agent] for cap, states in per_cap.items()} for agent in AGENTS}

    def _deploy_rules(self) -> dict[str, bool]:
        h = self._home
        return {
            "claude": (h / ".claude" / "CLAUDE.md").exists(),
            "cursor": self._count_cursor_rules(self._cursor_rules_dir()) > 0,
            "codex": (h / ".codex" / "AGENTS.md").exists(),
            "gemini": (h / ".gemini" / "AGENTS.md").exists(),
            "pi": (h / ".pi" / "agent" / "AGENTS.md").exists(),
        }

    def _deploy_skills(self) -> dict[str, bool]:
        h = self._home
        return {
            "claude": self._count_subdirs(h / ".claude" / "skills") > 0,
            "cursor": self._count_subdirs(h / ".cursor" / "skills") > 0,
            "codex": self._count_subdirs(h / ".agents" / "skills") > 0,
            "gemini": self._count_subdirs(h / ".gemini" / "antigravity-cli" / "skills") > 0,
            "pi": self._count_subdirs(h / ".agents" / "skills") > 0,
        }

    def _deploy_subagents(self) -> dict[str, bool]:
        h = self._home
        return {
            "claude": self._has_md(h / ".claude" / "agents"),
            "cursor": self._has_md(h / ".cursor" / "agents"),
            "codex": self._has_md(h / ".codex" / "agents"),
            "gemini": False,  # supported, but no .md-dir convention yet (inline)
            "pi": self._has_md(h / ".pi" / "agent" / "agents"),
        }

    def _deploy_statusline(self) -> dict[str, bool]:
        h = self._home
        return {
            "claude": self._file_contains(h / ".claude" / "settings.json", "statusLine"),
            "cursor": False,  # beta; no stable deploy mechanism yet
            "codex": self._file_contains(h / ".codex" / "config.toml", "status_line"),
            # agy ships a native, always-on statusline (no file to deploy); the
            # presence of its config root proves agy is set up and the bar is shown.
            "gemini": (h / ".gemini" / "antigravity-cli").is_dir(),
            "pi": (h / ".pi" / "agent" / "extensions" / "git-status.ts").exists(),
        }

    def _deploy_permissions(self) -> dict[str, bool]:
        h = self._home
        return {
            "claude": self._file_contains(h / ".claude" / "settings.json", "permissions"),
            "cursor": (h / ".cursor" / "cli-config.json").exists(),
            "codex": (h / ".codex" / "rules" / "default.rules").exists(),
            "gemini": (h / ".gemini" / "settings.json").exists(),
            "pi": (h / ".pi" / "agent" / "permission-policy.json").exists(),
        }

    def _deploy_hooks(self) -> dict[str, bool]:
        rows = self.section_hooks()
        return {
            "claude": any(r.claude for r in rows),
            "cursor": any(r.cursor for r in rows),
            "codex": any(r.codex for r in rows),
            "gemini": False,  # no hooks deployed
            "pi": False,  # hooks only via the safe-git extension, not our shared set
        }

    def _has_md(self, path: Path) -> bool:
        """True when *path* is a dir holding at least one ``.md`` file."""
        return path.is_dir() and any(p.suffix == ".md" for p in list_dir(path))

    def _file_contains(self, path: Path, needle: str) -> bool:
        """True when *path* exists and its text contains *needle*."""
        return needle in self._read_text(path)

    # ------------------------------------------------------------------
    # Skills & Rules (colocated value matrix: per-agent deployment)
    # ------------------------------------------------------------------

    def section_skills_rules(self) -> list[ValueRow]:
        """Per-agent skill counts and where each vendor's rules live (files vs embedded)."""
        h = self._home
        skills = {
            "claude": str(self._count_subdirs(h / ".claude" / "skills")),
            "cursor": str(self._count_subdirs(h / ".cursor" / "skills")),
            "codex": str(self._count_subdirs(h / ".agents" / "skills")),
            "gemini": "—",  # Gemini has no skills surface
            "pi": str(self._count_subdirs(h / ".agents" / "skills")),
        }
        # The kernel (rules.md) is deployed verbatim to each vendor's instruction
        # file — the cell names that file, consistently, so every vendor reads the
        # same rules via its own convention (Claude=CLAUDE.md, Cursor=.mdc, rest=AGENTS.md).
        rules = {
            "claude": "CLAUDE" if (h / ".claude" / "CLAUDE.md").exists() else "—",
            "cursor": ".mdc" if self._count_cursor_rules(self._cursor_rules_dir()) > 0 else "—",
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
        """Per-vendor hook coverage by intent, not raw native event name.

        Every hook-capable vendor wires the same shared scripts through different
        native events. An intent is present for a vendor when its script basename
        appears in that vendor's hook config.
        """
        agents_dir = self._dotfiles / "ai" / "agents"
        texts = {
            "claude": self._read_text(agents_dir / "claude" / "hooks.json"),
            "cursor": self._read_text(agents_dir / "cursor" / "hooks" / "hooks.json"),
            "codex": self._read_text(agents_dir / "codex" / "hooks.json"),
        }
        return [
            HookRow(
                event=intent,
                claude=script in texts["claude"],
                cursor=script in texts["cursor"],
                codex=script in texts["codex"],
            )
            for intent, script in _HOOK_INTENTS
        ]

    def _read_text(self, path: Path) -> str:
        """File text, or '' when absent/unreadable."""
        try:
            return path.read_text()
        except OSError:
            return ""

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

        cursor_dir = self._home / ".cursor" / "skills"
        cursor_deployed = self._count_subdirs(cursor_dir)

        shared_dir = self._home / ".agents" / "skills"
        shared_deployed = self._count_subdirs(shared_dir)

        return SkillsSummary(
            canonical_skills=canonical,
            claude_deployed=claude_deployed,
            cursor_deployed=cursor_deployed,
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

        # One dir per vendor that reads a `.md` subagents directory. Cursor 2.4+
        # reads ~/.cursor/agents (we deploy there); agy has no confirmed .md dir
        # convention yet (it defines subagents inline), so it's an honest gap.
        claude_agents = self._home / ".claude" / "agents"
        codex_agents = self._home / ".codex" / "agents"
        cursor_agents = self._home / ".cursor" / "agents"
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
                    cursor=(cursor_agents / f"{name}.md").exists(),
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
