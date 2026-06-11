"""Skill-health: deployment counts, canonical-vs-deployed drift, and MCP probes.

Composes AgentOverviewService (counts/drift) with a small MCP-reachability probe.
HTTP servers are probed over the HttpClient port; stdio servers are checked for
presence on PATH (we never launch them). `offline` skips all probing.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from dotfiles.adapters.ports import HttpClient, HttpError, ProcessRunner
from dotfiles.agent import OVERVIEW_AGENTS, VENDOR_BY_NAME, Agent
from dotfiles.cmd.agent.config import McpServerEntry, load_mcp_servers
from dotfiles.cmd.agent.models import AgentOverview, AgentVerify, McpProbe
from dotfiles.cmd.agent.overview import AgentOverviewService


def probe_mcp(
    server: str,
    entry: McpServerEntry,
    *,
    http: HttpClient,
    which: Callable[[str], str | None] = shutil.which,
) -> McpProbe:
    """Probe one MCP server. HTTP: try to reach the URL. stdio: command on PATH?"""
    if entry.url:
        return _probe_http(server, entry.url, http)
    if entry.command:
        on_path = which(entry.command) is not None
        detail = f"{entry.command} on PATH" if on_path else f"{entry.command} not found"
        return McpProbe(server=server, ok=on_path, detail=detail)
    return McpProbe(server=server, ok=False, detail="no url or command configured")


def _probe_http(server: str, url: str, http: HttpClient) -> McpProbe:
    """Reachability of an HTTP MCP endpoint — any server answer counts as live."""
    try:
        http.get_json(url)
    except HttpError as exc:
        # The server answered with an HTTP status → the endpoint is live. MCP HTTP
        # servers commonly reject a bare GET (405) since they speak POST/streaming,
        # so any status means reachable. Only a status-less error (DNS/TLS/connection
        # failure) is a genuine miss.
        if exc.status is not None:
            return McpProbe(server=server, ok=True, detail=f"reachable (HTTP {exc.status})")
        return McpProbe(server=server, ok=False, detail=str(exc)[:60])
    except OSError as exc:
        return McpProbe(server=server, ok=False, detail=str(exc)[:60])
    except ValueError:
        # Got a response, just not JSON — the endpoint is reachable.
        return McpProbe(server=server, ok=True, detail="reachable (non-JSON)")
    return McpProbe(server=server, ok=True, detail="reachable")


def _vendor_counts(overview: AgentOverview, agent: Agent) -> tuple[int, int, int, int]:
    """Return (skills_deployed, skills_expected, agents_deployed, agents_expected)."""
    canonical = overview.skills.canonical_skills
    # Every vendor that deploys our skills is in the registry-built map; expected
    # is the canonical count for those, 0 for a vendor with no skills surface.
    deployed = overview.skills.deployed
    skills_dep = deployed.get(agent, 0)
    skills_exp = canonical if agent in deployed else 0

    # Every vendor with a subagents dir is expected to carry the full set — derived
    # from the registry, never hand-listed, so verify agrees with the overview (which
    # reads the same field). A vendor with no subagents surface expects 0.
    if VENDOR_BY_NAME[agent].paths.subagents:
        agents_dep = sum(1 for a in overview.agents if a.cells.get(agent, False))
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
    agent: Agent,
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
        if agent in entry.targets
    )


def build_vendor_verifies(
    overview: AgentOverview,
    mcp_servers: dict[str, McpServerEntry],
    *,
    http: HttpClient,
    which: Callable[[str], str | None] = shutil.which,
    offline: bool = False,
) -> list[AgentVerify]:
    """Per-agent skill-health from an AgentOverview + the MCP server config."""
    verifies: list[AgentVerify] = []
    for agent in OVERVIEW_AGENTS:
        skills_dep, skills_exp, agents_dep, agents_exp = _vendor_counts(overview, agent)
        verifies.append(
            AgentVerify(
                agent=agent,
                skills_deployed=skills_dep,
                skills_expected=skills_exp,
                agents_deployed=agents_dep,
                agents_expected=agents_exp,
                drift=_drift(skills_dep, skills_exp, agents_dep, agents_exp),
                mcp=_vendor_probes(agent, mcp_servers, http=http, which=which, offline=offline),
            )
        )
    return verifies


class SkillHealthService:
    """Wires AgentOverviewService + MCP config into per-agent skill-health."""

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

    def verify(self, *, offline: bool = False) -> list[AgentVerify]:
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
