"""Skill-health: deployment counts, drift, and MCP reachability probes."""

from dotfiles.adapters.ports import HttpError
from dotfiles.cmd.agent.config import McpServerEntry
from dotfiles.cmd.agent.models import (
    AgentOverview,
    AgentPresenceRow,
    AgentVerify,
    McpProbe,
)
from dotfiles.cmd.agent.skill_census import SkillCensus
from dotfiles.cmd.agent.skill_health import SkillHealthService, build_vendor_verifies, probe_mcp
from dotfiles.testing.fakes import FakeHttpClient, FakeProcessRunner


def test_vendor_verify_holds_counts_drift_and_probes():
    v = AgentVerify(
        agent="claude",
        skills_ours=21,
        skills_expected=21,
        skills_external=2,
        skills_foreign=0,
        agents_deployed=6,
        agents_expected=6,
        drift=(),
        mcp=(McpProbe(server="granola", ok=True, detail="reachable"),),
    )
    assert v.agent == "claude"
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


class _HttpNonJson(FakeHttpClient):
    """A 2xx response whose body isn't JSON — json.loads raises ValueError."""

    def get_json(self, url):  # type: ignore[override]
        raise ValueError("Expecting value: line 1 column 1")


def test_probe_http_non_json_body_is_reachable():
    # An endpoint that answers a GET with non-JSON (a ValueError on decode) is
    # still reachable. Flagged by an adversarial-assessor pass as an uncovered
    # branch the FakeHttpClient couldn't reach.
    entry = McpServerEntry.model_validate(
        {"targets": ["claude"], "type": "http", "url": "https://x/mcp"}
    )
    probe = probe_mcp("granola", entry, http=_HttpNonJson(), which=lambda c: c)
    assert probe.ok is True
    assert "non-JSON" in probe.detail


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


class _HttpStatus(FakeHttpClient):
    """Answers with an HTTP error status — the server is live but rejects GET."""

    def get_json(self, url):  # type: ignore[override]
        raise HttpError("HTTP 405: Method Not Allowed", status=405)


class _HttpConnFail(FakeHttpClient):
    """Connection never completes — no status."""

    def get_json(self, url):  # type: ignore[override]
        raise HttpError("Connection failed", status=None)


def test_probe_http_405_is_reachable():
    # Regression: an MCP server returning 405 to a GET (it speaks POST) must be
    # reported reachable, not crash `agent verify` with an unhandled HttpError.
    entry = McpServerEntry.model_validate(
        {"targets": ["claude"], "type": "http", "url": "https://x/mcp"}
    )
    probe = probe_mcp("granola", entry, http=_HttpStatus(), which=lambda c: c)
    assert probe.ok is True
    assert "405" in probe.detail


def test_probe_http_connection_failure_is_unreachable():
    entry = McpServerEntry.model_validate(
        {"targets": ["claude"], "type": "http", "url": "https://x/mcp"}
    )
    probe = probe_mcp("granola", entry, http=_HttpConnFail(), which=lambda c: c)
    assert probe.ok is False


def test_probe_stdio_checks_path():
    entry = McpServerEntry.model_validate({"targets": ["claude"], "command": "npx"})
    present = probe_mcp("playwright", entry, http=FakeHttpClient(), which=lambda c: "/bin/npx")
    absent = probe_mcp("playwright", entry, http=FakeHttpClient(), which=lambda c: None)
    assert present.ok is True
    assert absent.ok is False


def _census(vendor: str, ours: int, expected: int, foreign: int = 0) -> SkillCensus:
    return SkillCensus(vendor=vendor, ours=ours, external=0, foreign=foreign, expected=expected)


def _overview(*, claude_deployed=21, canonical=21) -> AgentOverview:
    return AgentOverview(
        mcp=(),
        mcp_agents=(),
        hooks=(),
        censuses=(
            _census("claude", claude_deployed, canonical),
            _census("cursor", canonical, canonical),
            _census("codex", canonical, canonical),
        ),
        agents=(
            AgentPresenceRow(
                label="debugger",
                cells={"claude": True, "codex": True, "pi": False},
            ),
            AgentPresenceRow(
                label="security-auditor",
                cells={"claude": False, "codex": True, "pi": False},
            ),
        ),
        permissions=(),
    )


def test_build_vendor_verifies_flags_skill_drift():
    verifies = build_vendor_verifies(
        _overview(claude_deployed=19, canonical=21),
        mcp_servers={},
        http=FakeHttpClient(),
        which=lambda c: c,
        offline=True,
    )
    claude = next(v for v in verifies if v.agent == "claude")
    assert claude.skills_ours == 19
    assert claude.skills_expected == 21
    assert any("skills" in d for d in claude.drift)


def test_build_vendor_verifies_counts_agents_per_vendor():
    verifies = build_vendor_verifies(
        _overview(), mcp_servers={}, http=FakeHttpClient(), which=lambda c: c, offline=True
    )
    claude = next(v for v in verifies if v.agent == "claude")
    codex = next(v for v in verifies if v.agent == "codex")
    assert claude.agents_deployed == 1  # only debugger has claude=True
    assert codex.agents_deployed == 2
    # claude is missing one agent (security-auditor) -> drift recorded
    assert any("agents" in d for d in claude.drift)


def test_build_vendor_verifies_offline_skips_probes():
    verifies = build_vendor_verifies(
        _overview(),
        mcp_servers={
            "granola": McpServerEntry.model_validate({"targets": ["claude"], "url": "https://x"})
        },
        http=_RaisingHttp(),
        which=lambda c: c,
        offline=True,
    )
    claude = next(v for v in verifies if v.agent == "claude")
    assert claude.mcp == ()


def test_skill_health_service_runs_over_empty_tree(tmp_path):
    svc = SkillHealthService(
        runner=FakeProcessRunner(),
        http=FakeHttpClient(),
        dotfiles_dir=tmp_path / "d",
        home=tmp_path / "h",
        which=lambda c: None,
    )
    verifies = svc.verify(offline=True)
    assert {v.agent for v in verifies} == {"claude", "cursor", "codex", "gemini", "pi", "hermes"}
