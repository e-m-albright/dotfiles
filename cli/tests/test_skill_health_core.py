"""Skill-health: deployment counts, drift, and MCP reachability probes."""

from dotfiles.core.agent_config import McpServerEntry
from dotfiles.core.models import McpProbe, VendorVerify


def test_vendor_verify_holds_counts_drift_and_probes():
    v = VendorVerify(
        vendor="claude",
        skills_deployed=21,
        skills_expected=21,
        agents_deployed=6,
        agents_expected=6,
        drift=(),
        mcp=(McpProbe(server="granola", ok=True, detail="reachable"),),
    )
    assert v.vendor == "claude"
    assert v.mcp[0].ok is True


def test_mcp_entry_parses_transport_fields():
    http_entry = McpServerEntry.model_validate(
        {"targets": ["claude"], "type": "http", "url": "https://x/mcp"}
    )
    assert http_entry.url == "https://x/mcp"
    assert http_entry.kind == "http"
    stdio_entry = McpServerEntry.model_validate({"targets": ["claude"], "command": "npx"})
    assert stdio_entry.command == "npx"
    # backward-compat: targets-only still parses
    assert McpServerEntry.model_validate({"targets": ["cursor"]}).url is None
