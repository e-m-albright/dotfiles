"""Skill-health: deployment counts, drift, and MCP reachability probes."""

from dotfiles.core.agent_config import McpServerEntry
from dotfiles.core.models import McpProbe, VendorVerify
from dotfiles.core.skill_health import probe_mcp
from tests.fakes import FakeHttpClient


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


class _RaisingHttp(FakeHttpClient):
    def get_json(self, url):  # type: ignore[override]
        raise OSError("connection refused")


def test_probe_http_reachable():
    entry = McpServerEntry.model_validate(
        {"targets": ["claude"], "type": "http", "url": "https://x/mcp"}
    )
    probe = probe_mcp("granola", entry, http=FakeHttpClient(), which=lambda c: c)
    assert probe.ok is True
    assert probe.server == "granola"


def test_probe_http_unreachable():
    entry = McpServerEntry.model_validate(
        {"targets": ["claude"], "type": "http", "url": "https://x/mcp"}
    )
    probe = probe_mcp("granola", entry, http=_RaisingHttp(), which=lambda c: c)
    assert probe.ok is False
    assert "refused" in probe.detail


def test_probe_stdio_checks_path():
    entry = McpServerEntry.model_validate({"targets": ["claude"], "command": "npx"})
    present = probe_mcp("playwright", entry, http=FakeHttpClient(), which=lambda c: "/bin/npx")
    absent = probe_mcp("playwright", entry, http=FakeHttpClient(), which=lambda c: None)
    assert present.ok is True
    assert absent.ok is False
