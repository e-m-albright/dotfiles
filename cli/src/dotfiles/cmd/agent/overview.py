"""Agent overview service — every section a projection of the fleet model.

CAN comes from the capability matrix, STANCE from the VENDORS registry, HAVE
from ``build_fleet``'s live probes, skill numbers from the one census. This
module composes those into the dashboard sections; it owns no vendor lists,
no deploy paths, and no probe logic of its own — so the sections cannot
disagree with each other or with ``agent verify``.

Hexagonal: imports only stdlib + pydantic + core models/ports.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles.agent import AGENTS, HOOK_INTENTS, VENDORS, surface_path
from dotfiles.cmd.agent.capability_matrix import (
    CapabilityRow,
    capability_rows,
    fleet_doc_stale_days,
)
from dotfiles.cmd.agent.config import (
    InstalledPlugins,
    McpServersFile,
    PermissionsBlock,
    SettingsWithPermissions,
    load_config,
    load_mcp_servers,
)
from dotfiles.cmd.agent.fleet import Fleet, FleetCell, build_fleet
from dotfiles.cmd.agent.models import (
    AgentOverview,
    AgentPresenceRow,
    CoverageState,
    PermissionRow,
    PluginRow,
    UniformityRow,
    ValueRow,
)
from dotfiles.cmd.agent.skill_census import SkillCensus, skill_census
from dotfiles.cmd.agent.vendors.claude import parse_plugins_yaml
from dotfiles.cmd.agent.verify import vendor_surfaces
from dotfiles.fsutil import list_dir
from dotfiles.logging import get_logger

_log = get_logger(__name__)

if TYPE_CHECKING:
    from dotfiles.adapters.ports import ProcessRunner


# Capabilities we hold every vendor to a uniform standard on (the rest are
# tracked but not enforced). Each name is both a capability-matrix key and a
# registry surface name.
_ENFORCED_TIER: tuple[str, ...] = (
    "rules",
    "skills",
    "subagents",
    "statusline",
    "permissions",
    "hooks",
)

# Capability statuses that mean "the vendor supports it" for gap classification.
_SUPPORTED = ("yes", "beta", "ext")


def _coverage(cell: FleetCell) -> CoverageState:
    """Classify one fleet cell for the uniformity matrix: active / gap / local / na."""
    if cell.stance == "deploy":
        return "active" if cell.have is not None and cell.have.state == "present" else "gap"
    if cell.stance == "native":
        return "active"
    if cell.stance == "local":
        return "local"
    return "gap" if cell.can.status in _SUPPORTED else "na"


def _perm_settings(label: str, path: Path) -> list[PermissionRow]:
    cfg = load_config(path, SettingsWithPermissions)
    if cfg is None:
        return []
    return [
        PermissionRow(
            label=label,
            allow=len(cfg.permissions.allow),
            deny=len(cfg.permissions.deny),
            source_path=str(path),
        )
    ]


def _perm_permissions_block(label: str, path: Path) -> list[PermissionRow]:
    cfg = load_config(path, PermissionsBlock)
    if cfg is None:
        return []
    return [
        PermissionRow(
            label=label,
            allow=len(cfg.allow),
            deny=len(cfg.deny),
            source_path=str(path),
        )
    ]


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
        """Build the fleet once, then project every section from it."""
        fleet = self.fleet()
        return AgentOverview(
            mcp=tuple(self.section_mcp()),
            mcp_agents=self._mcp_deploy_targets(),
            hooks=tuple(self.section_hooks(fleet)),
            agents=tuple(self.section_agents()),
            permissions=tuple(self.section_permissions()),
            vendor_surfaces=tuple(
                vendor_surfaces(fleet, home=self._home, dotfiles_dir=self._dotfiles)
            ),
            plugins=tuple(self.section_plugins()),
            censuses=tuple(self.section_censuses()),
            skills_rules=tuple(self.section_skills_rules(fleet)),
            capabilities=tuple(self.section_capabilities()),
            uniformity=tuple(self.section_uniformity(fleet)),
            fleet_doc_stale_days=fleet_doc_stale_days(self._dotfiles, date.today()),
        )

    def fleet(self) -> Fleet:
        """The single CAN x STANCE x HAVE model every section projects from."""
        return build_fleet(home=self._home, dotfiles_dir=self._dotfiles)

    def section_capabilities(self) -> list[CapabilityRow]:
        """The cross-vendor capability matrix (vendor support + provenance)."""
        return capability_rows()

    def section_uniformity(self, fleet: Fleet) -> list[UniformityRow]:
        """Per-vendor coverage of the enforced tier — a pure fleet projection."""
        return [
            UniformityRow(
                capability=cap,
                cells={agent: _coverage(fleet.cell(agent, cap)) for agent in AGENTS},
            )
            for cap in _ENFORCED_TIER
        ]

    # ------------------------------------------------------------------
    # Skills (one census; every skill number anywhere comes from here)
    # ------------------------------------------------------------------

    def section_censuses(self) -> list[SkillCensus]:
        """One census per vendor with a skills deploy."""
        return [
            census
            for v in VENDORS
            if (census := skill_census(v, home=self._home, dotfiles_dir=self._dotfiles)) is not None
        ]

    def _rules_cell(self, fleet: Fleet, agent: str) -> str:
        cell = fleet.cell(agent, "rules")
        if cell.stance != "deploy" or cell.have is None or cell.have.state != "present":
            return "—"
        if agent == "cursor":
            return ".mdc"
        return "CLAUDE" if agent == "claude" else "AGENTS"

    def section_skills_rules(self, fleet: Fleet) -> list[ValueRow]:
        """Per-agent skill counts (census labels) and where each vendor's rules live."""
        by_vendor = {c.vendor: c for c in self.section_censuses()}
        skills = {
            v.name: by_vendor[v.name].label() if v.name in by_vendor else "—" for v in VENDORS
        }
        rules = {v.name: self._rules_cell(fleet, v.name) for v in VENDORS}
        return [
            ValueRow(label="skills", cells=skills),
            ValueRow(label="rules", cells=rules),
        ]

    # ------------------------------------------------------------------
    # Section: MCP Servers
    # ------------------------------------------------------------------

    def section_mcp(self) -> list[AgentPresenceRow]:
        """One row per server, from each agent's LIVE config (codex via `codex mcp list`)."""
        live = self._live_mcp()
        names = sorted({name for servers in live.values() for name in servers})
        return [
            AgentPresenceRow(
                label=name,
                cells={agent: name in live[agent] for agent in AGENTS},
            )
            for name in names
        ]

    def _mcp_deploy_targets(self) -> tuple[str, ...]:
        """Vendors any MCP server in the shared registry targets — the deploy intent.

        Derived from mcp-servers.json (the file that drives setup's MCP merge),
        so the overview's "applies" set and the deploy behaviour share a source.
        """

        registry = load_mcp_servers(
            self._dotfiles / "ai" / "agents" / "shared" / "mcp-servers.json"
        )
        targets = {t for entry in registry.values() for t in entry.targets}
        return tuple(a for a in AGENTS if a in targets)

    def _live_mcp(self) -> dict[str, set[str]]:
        """Server names actually configured per agent, read from live state."""
        h = self._home
        live: dict[str, set[str]] = {}
        for v in VENDORS:
            deploy = v.deploy("mcp")
            if v.name == "codex":
                live["codex"] = self._codex_mcp()
            elif deploy is None:
                live[v.name] = set()
            else:
                live[v.name] = self._mcp_config_servers(h / deploy.path)
        return live

    def _mcp_config_servers(self, path: Path) -> set[str]:
        """The ``mcpServers`` keys in an agent's MCP config (empty if absent/invalid)."""
        cfg = load_config(path, McpServersFile)
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
        cfg = load_config(config, InstalledPlugins)
        if cfg is None:
            return []
        declared = self._declared_plugin_names()
        rows: list[PluginRow] = []
        for ref, installs in cfg.plugins.items():
            name, _, marketplace = str(ref).partition("@")
            version = installs[0].version if installs else ""
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
    # Section: Hooks (per intent, probed from the LIVE deployed configs)
    # ------------------------------------------------------------------

    def section_hooks(self, fleet: Fleet) -> list[AgentPresenceRow]:
        """Per-vendor hook coverage by intent, proven against the live hooks config.

        A vendor participates iff its registry hooks stance is a hook-intents
        deploy; presence per intent = the shared script's basename appearing in
        that vendor's deployed config text (not the repo source — what's wired,
        not what we'd wire).
        """
        texts: dict[str, str] = {}
        for v in VENDORS:
            deploy = v.deploy("hooks")
            if deploy is not None and deploy.proof == "hook-intents":
                texts[v.name] = self._read_text(self._home / deploy.path)
        return [
            AgentPresenceRow(
                label=intent,
                cells={
                    agent: script in texts[agent] if agent in texts else False for agent in AGENTS
                },
            )
            for intent, script in HOOK_INTENTS
        ]

    def _read_text(self, path: Path) -> str:
        """File text, or '' when absent/unreadable.

        A present-but-unreadable file (permissions, broken mount) degrades to ''
        like an absent one, so the probe can't crash. That collapse is logged so
        a misdiagnosis ("not deployed" when really "couldn't read") is traceable.
        """
        try:
            return path.read_text()
        except FileNotFoundError:
            return ""
        except OSError as exc:
            _log.warning("probe_read_failed", path=str(path), error=str(exc))
            return ""

    # ------------------------------------------------------------------
    # Section: Subagents
    # ------------------------------------------------------------------

    def section_agents(self) -> list[AgentPresenceRow]:
        """One row per subagent .md, with deployment flags per vendor."""
        agents_root = self._dotfiles / "ai" / "subagents"
        if not agents_root.exists() or not agents_root.is_dir():
            return []

        h = self._home
        deploy_dirs = {
            v.name: h / d.path if (d := v.deploy("subagents")) else None for v in VENDORS
        }
        rows: list[AgentPresenceRow] = []
        for entry in list_dir(agents_root):
            if entry.is_dir() or entry.suffix != ".md":
                continue
            name = entry.stem
            rows.append(
                AgentPresenceRow(
                    label=name,
                    cells={
                        agent: (
                            (dest / f"{name}.md").exists()
                            if (dest := deploy_dirs[agent]) is not None
                            else False
                        )
                        for agent in AGENTS
                    },
                )
            )
        return rows

    # ------------------------------------------------------------------
    # Section: Permissions
    # ------------------------------------------------------------------

    def section_permissions(self) -> list[PermissionRow]:
        """One PermissionRow per config source that exists."""
        rows: list[PermissionRow] = []
        rows.extend(
            _perm_settings("Claude Code (deployed)", surface_path(self._home, "claude", "settings"))
        )
        rows.extend(
            _perm_permissions_block(
                "Claude (dotfiles source)",
                self._dotfiles / "ai" / "agents" / "claude" / "permissions.json",
            )
        )
        rows.extend(
            _perm_settings(
                "Cursor CLI",
                self._dotfiles / "ai" / "agents" / "cursor" / "cli-config.json",
            )
        )
        rows.extend(self._perm_codex())
        return rows

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
