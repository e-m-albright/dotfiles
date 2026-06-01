"""Skill-health: deployment counts, canonical-vs-deployed drift, and MCP probes.

Composes AgentOverviewService (counts/drift) with a small MCP-reachability probe.
HTTP servers are probed over the HttpClient port; stdio servers are checked for
presence on PATH (we never launch them). `offline` skips all probing.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable

from dotfiles.core.agent_config import McpServerEntry
from dotfiles.core.models import McpProbe
from dotfiles.core.ports import HttpClient

_VENDORS = ("claude", "cursor", "codex", "gemini")


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
