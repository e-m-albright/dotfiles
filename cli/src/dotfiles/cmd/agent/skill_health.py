"""Skill-health: deployment counts, canonical-vs-deployed drift, and MCP probes.

Composes AgentOverviewService (counts/drift) with a small MCP-reachability probe.
HTTP servers are probed over the HttpClient port; stdio servers are checked for
presence on PATH (we never launch them). `offline` skips all probing.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from dotfiles.adapters.ports import HttpClient, ProcessRunner
from dotfiles.cmd.agent.config import McpServerEntry, load_mcp_servers
from dotfiles.cmd.agent.models import AgentOverview, McpProbe, VendorVerify
from dotfiles.cmd.agent.overview import AgentOverviewService
from dotfiles.vendor import OVERVIEW_VENDORS, Vendor


def probe_mcp(
    server: str,
    entry: McpServerEntry,
    *,
    http: HttpClient,
    which: Callable[[str], str | None] = shutil.which,
) -> McpProbe:
    """Probe one MCP server. HTTP: try to reach the URL. stdio: command on PATH?"""
    if entry.url:
        try:
            http.get_json(entry.url)
        except OSError as exc:
            return McpProbe(server=server, ok=False, detail=str(exc)[:60])
        except ValueError:
            # Got a response, just not JSON — the endpoint is reachable.
            return McpProbe(server=server, ok=True, detail="reachable (non-JSON)")
        return McpProbe(server=server, ok=True, detail="reachable")
    if entry.command:
        if which(entry.command) is not None:
            return McpProbe(server=server, ok=True, detail=f"{entry.command} on PATH")
        return McpProbe(server=server, ok=False, detail=f"{entry.command} not found")
    return McpProbe(server=server, ok=False, detail="no url or command configured")


def _vendor_counts(overview: AgentOverview, vendor: Vendor) -> tuple[int, int, int, int]:
    """Return (skills_deployed, skills_expected, agents_deployed, agents_expected)."""
    canonical = overview.skills.canonical_skills
    if vendor == "claude":
        skills_dep, skills_exp = overview.skills.claude_deployed, canonical
    elif vendor == "codex":
        skills_dep, skills_exp = overview.skills.shared_deployed, canonical
    else:
        skills_dep, skills_exp = 0, 0

    if vendor in ("claude", "codex"):
        agents_dep = sum(1 for a in overview.agents if getattr(a, vendor, False))
        agents_exp = len(overview.agents)
    else:
        agents_dep, agents_exp = 0, 0
    return skills_dep, skills_exp, agents_dep, agents_exp


def _drift(skills_dep: int, skills_exp: int, agents_dep: int, agents_exp: int) -> tuple[str, ...]:
    drift: list[str] = []
    if skills_exp and skills_dep != skills_exp:
        drift.append(f"skills {skills_dep}/{skills_exp} deployed")
    if agents_exp and agents_dep != agents_exp:
        drift.append(f"agents {agents_dep}/{agents_exp} deployed")
    return tuple(drift)


def _vendor_probes(
    vendor: Vendor,
    mcp_servers: dict[str, McpServerEntry],
    *,
    http: HttpClient,
    which: Callable[[str], str | None],
    offline: bool,
) -> tuple[McpProbe, ...]:
    if offline:
        return ()
    return tuple(
        probe_mcp(name, entry, http=http, which=which)
        for name, entry in mcp_servers.items()
        if vendor in entry.targets
    )


def build_vendor_verifies(
    overview: AgentOverview,
    mcp_servers: dict[str, McpServerEntry],
    *,
    http: HttpClient,
    which: Callable[[str], str | None] = shutil.which,
    offline: bool = False,
) -> list[VendorVerify]:
    """Per-vendor skill-health from an AgentOverview + the MCP server config."""
    verifies: list[VendorVerify] = []
    for vendor in OVERVIEW_VENDORS:
        skills_dep, skills_exp, agents_dep, agents_exp = _vendor_counts(overview, vendor)
        verifies.append(
            VendorVerify(
                vendor=vendor,
                skills_deployed=skills_dep,
                skills_expected=skills_exp,
                agents_deployed=agents_dep,
                agents_expected=agents_exp,
                drift=_drift(skills_dep, skills_exp, agents_dep, agents_exp),
                mcp=_vendor_probes(vendor, mcp_servers, http=http, which=which, offline=offline),
            )
        )
    return verifies


class SkillHealthService:
    """Wires AgentOverviewService + MCP config into per-vendor skill-health."""

    def __init__(
        self,
        *,
        runner: ProcessRunner,
        http: HttpClient,
        dotfiles_dir: Path,
        home: Path,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self._runner = runner
        self._http = http
        self._dotfiles = dotfiles_dir
        self._home = home
        self._which = which

    def verify(self, *, offline: bool = False) -> list[VendorVerify]:
        overview = AgentOverviewService(
            runner=self._runner,
            dotfiles_dir=self._dotfiles,
            home=self._home,
            which=self._which,
        ).overview()
        mcp_servers = load_mcp_servers(
            self._dotfiles / "ai" / "agents" / "shared" / "mcp-servers.json"
        )
        return build_vendor_verifies(
            overview,
            mcp_servers,
            http=self._http,
            which=self._which,
            offline=offline,
        )
