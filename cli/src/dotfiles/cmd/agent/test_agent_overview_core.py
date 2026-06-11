"""Tests for AgentOverviewService — all sections, no FakeFileSystem."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dotfiles.cmd.agent.models import AgentOverview, AgentSurface
from dotfiles.cmd.agent.overview import AgentOverviewService
from dotfiles.testing.fakes import FakeProcessRunner


def make_service(dotfiles: Path, home: Path) -> AgentOverviewService:
    return AgentOverviewService(
        runner=FakeProcessRunner(),
        dotfiles_dir=dotfiles,
        home=home,
    )


# ---------------------------------------------------------------------------
# Helpers to seed filesystem
# ---------------------------------------------------------------------------


def seed_claude_hooks(dotfiles: Path, hooks_dict: dict) -> None:
    path = dotfiles / "ai" / "agents" / "claude" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"hooks": hooks_dict}))


def seed_codex_hooks(dotfiles: Path, hooks_dict: dict) -> None:
    path = dotfiles / "ai" / "agents" / "codex" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"hooks": hooks_dict}))


def seed_skill(dotfiles: Path, name: str) -> None:
    skill_dir = dotfiles / "ai" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"# {name}")


def seed_agent(dotfiles: Path, name: str) -> None:
    agents_root = dotfiles / "ai" / "subagents"
    agents_root.mkdir(parents=True, exist_ok=True)
    (agents_root / f"{name}.md").write_text(f"# {name}")


def seed_rule(dotfiles: Path, name: str) -> None:
    rules_root = dotfiles / "ai" / "rules" / "process"
    rules_root.mkdir(parents=True, exist_ok=True)
    (rules_root / f"{name}.mdc").write_text(f"# {name}")


# ===========================================================================
# Section 1: MCP Servers
# ===========================================================================


def _service_with_runner(
    dotfiles: Path, home: Path, runner: FakeProcessRunner
) -> AgentOverviewService:
    return AgentOverviewService(runner=runner, dotfiles_dir=dotfiles, home=home)


def _runner_codex_mcp(*servers: str) -> FakeProcessRunner:
    """A runner whose `codex mcp list` reports the given servers as enabled."""
    runner = FakeProcessRunner()
    body = "Name  Command  Status\n" + "\n".join(f"{s}  npx  enabled" for s in servers)
    runner.script(("codex", "mcp", "list"), stdout=body)
    return runner


def _seed_mcp_config(home: Path, rel: str, servers: list[str]) -> None:
    """Write an agent's live MCP config (mcpServers map) at home/rel."""
    path = home / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"mcpServers": {s: {} for s in servers}}))


class TestSectionMcp:
    def test_empty_when_nothing_configured(self, tmp_path: Path) -> None:
        # default runner → `codex mcp list` returns empty; no agent configs on disk
        assert make_service(tmp_path / "d", tmp_path / "home").section_mcp() == []

    def test_per_agent_from_live_state(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        _seed_mcp_config(home, ".claude.json", ["granola", "playwright"])
        _seed_mcp_config(home, ".cursor/mcp.json", ["context7", "playwright"])
        _seed_mcp_config(home, ".gemini/settings.json", ["playwright"])
        runner = _runner_codex_mcp("playwright")

        rows = _service_with_runner(tmp_path / "d", home, runner).section_mcp()
        by = {r.label: r for r in rows}

        assert by["playwright"].cells["claude"]
        assert by["playwright"].cells["cursor"]
        assert by["playwright"].cells["codex"]
        assert by["playwright"].cells["gemini"]
        assert by["granola"].cells["claude"]
        assert by["granola"].cells["codex"] is False
        assert by["granola"].cells["cursor"] is False
        assert by["context7"].cells["cursor"]
        assert by["context7"].cells["claude"] is False
        # Pi has no MCP surface — always n/a (False), never a failure.
        assert all(r.cells.get("pi") is False for r in rows)

    def test_codex_servers_come_from_the_cli(self, tmp_path: Path) -> None:
        runner = _runner_codex_mcp("playwright")
        rows = _service_with_runner(tmp_path / "d", tmp_path / "home", runner).section_mcp()
        assert [r.label for r in rows] == ["playwright"]
        assert rows[0].cells["codex"] is True

    def test_codex_cli_failure_degrades_to_empty(self, tmp_path: Path) -> None:
        runner = FakeProcessRunner()
        runner.script(("codex", "mcp", "list"), exit_code=1)
        rows = _service_with_runner(tmp_path / "d", tmp_path / "home", runner).section_mcp()
        assert rows == []


# ===========================================================================
# Section 2: Hooks
# ===========================================================================


_SHARED = "~/dotfiles/ai/agents/shared/hooks"
_INTENT_SCRIPT = {
    "guard-file": f"{_SHARED}/guard-sensitive-file.sh",
    "guard-shell": f"{_SHARED}/guard-destructive-shell.sh",
    "format": f"{_SHARED}/format-on-save.sh",
    "notify": f"{_SHARED}/notify.sh",
}


def _seed_live_intents(home: Path, rel: str, intents: list[str]) -> None:
    """Write a vendor's LIVE hooks config at home/rel wiring the given intents."""
    path = home / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    cmds = [{"hooks": [{"command": _INTENT_SCRIPT[i]}]} for i in intents]
    path.write_text(json.dumps({"hooks": {"PreToolUse": cmds}}))


_CLAUDE_HOOKS = ".claude/settings.json"
_CURSOR_HOOKS = ".cursor/plugins/dotfiles/hooks/hooks.json"
_CODEX_HOOKS = ".codex/hooks.json"

_INTENT_NAMES = ["guard-file", "guard-shell", "format", "notify"]


def _hooks_rows(dotfiles: Path, home: Path):
    svc = make_service(dotfiles, home)
    return svc.section_hooks(svc.fleet())


class TestSectionHooks:
    def test_four_intent_rows_even_with_no_hook_files(self, tmp_path: Path) -> None:
        rows = _hooks_rows(tmp_path / "dotfiles", tmp_path / "home")
        assert [r.label for r in rows] == _INTENT_NAMES
        assert all(
            not (r.cells.get("claude") or r.cells.get("cursor") or r.cells.get("codex"))
            for r in rows
        )

    def test_intent_present_when_its_shared_script_is_wired_live(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        _seed_live_intents(home, _CLAUDE_HOOKS, ["guard-file", "guard-shell", "format", "notify"])
        rows = _hooks_rows(tmp_path / "dotfiles", home)
        assert all(r.cells["claude"] for r in rows)
        assert all(not r.cells.get("cursor") and not r.cells.get("codex") for r in rows)

    def test_per_vendor_intent_detection(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        _seed_live_intents(home, _CURSOR_HOOKS, ["format", "guard-shell"])
        _seed_live_intents(home, _CODEX_HOOKS, ["guard-file", "notify"])
        rows = {r.label: r for r in _hooks_rows(tmp_path / "dotfiles", home)}
        assert rows["format"].cells["cursor"]
        assert not rows["format"].cells["codex"]
        assert rows["guard-shell"].cells["cursor"]
        assert rows["guard-file"].cells["codex"]
        assert not rows["guard-file"].cells["cursor"]
        assert rows["notify"].cells["codex"]

    def test_uniform_intent_across_all_three_vendors(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        for rel in (_CLAUDE_HOOKS, _CURSOR_HOOKS, _CODEX_HOOKS):
            _seed_live_intents(home, rel, ["notify"])
        notify = next(r for r in _hooks_rows(tmp_path / "dotfiles", home) if r.label == "notify")
        assert notify.cells["claude"]
        assert notify.cells["cursor"]
        assert notify.cells["codex"]

    def test_invalid_json_graceful(self, tmp_path: Path) -> None:
        # The probe greps text, so even unparseable JSON yields four all-False rows.
        home = tmp_path / "home"
        path = home / _CLAUDE_HOOKS
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("BAD")
        rows = _hooks_rows(tmp_path / "dotfiles", home)
        assert [r.label for r in rows] == _INTENT_NAMES
        assert all(not r.cells.get("claude") for r in rows)

    def test_pi_rides_an_extension_not_the_intent_matrix(self, tmp_path: Path) -> None:
        # Pi's hooks deploy is the safe-git extension — never a shared-intent cell.
        rows = _hooks_rows(tmp_path / "dotfiles", tmp_path / "home")
        assert all(r.cells.get("pi") is False for r in rows)


_ENFORCED_TIER_NAMES = ["rules", "skills", "subagents", "statusline", "permissions", "hooks"]


def _uniformity(dotfiles: Path, home: Path):
    svc = make_service(dotfiles, home)
    return svc.section_uniformity(svc.fleet())


class TestSectionUniformity:
    def test_rows_are_the_enforced_tier(self, tmp_path: Path) -> None:
        rows = _uniformity(tmp_path / "d", tmp_path / "home")
        assert [r.capability for r in rows] == _ENFORCED_TIER_NAMES

    def test_supported_but_undeployed_is_a_gap(self, tmp_path: Path) -> None:
        # Empty home: claude supports rules (matrix) but nothing is deployed -> gap.
        rows = {r.capability: r for r in _uniformity(tmp_path / "d", tmp_path / "home")}
        assert rows["rules"].cells["claude"] == "gap"
        assert rows["hooks"].cells["claude"] == "gap"

    def test_deployed_capability_is_active(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude").mkdir(parents=True)
        (home / ".claude" / "CLAUDE.md").write_text("kernel")
        (home / ".claude" / "settings.json").write_text('{"statusLine": {}, "permissions": {}}')
        rows = {r.capability: r for r in _uniformity(tmp_path / "d", home)}
        assert rows["rules"].cells["claude"] == "active"
        assert rows["statusline"].cells["claude"] == "active"
        assert rows["permissions"].cells["claude"] == "active"

    def test_hooks_active_when_all_intents_wired_live(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        _seed_live_intents(home, _CLAUDE_HOOKS, ["guard-file", "guard-shell", "format", "notify"])
        rows = {r.capability: r for r in _uniformity(tmp_path / "d", home)}
        assert rows["hooks"].cells["claude"] == "active"

    def test_partially_wired_hooks_are_a_gap_not_active(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        _seed_live_intents(home, _CLAUDE_HOOKS, ["guard-file"])
        rows = {r.capability: r for r in _uniformity(tmp_path / "d", home)}
        assert rows["hooks"].cells["claude"] == "gap"

    def test_workspace_local_capabilities_are_not_closable_gaps(self, tmp_path: Path) -> None:
        # agy subagents/hooks (workspace-local) and cursor statusline (beta) are
        # supported but not closable by a global deploy -> "local".
        rows = {r.capability: r for r in _uniformity(tmp_path / "d", tmp_path / "home")}
        assert rows["subagents"].cells["gemini"] == "local"
        assert rows["hooks"].cells["gemini"] == "local"
        assert rows["statusline"].cells["cursor"] == "local"

    def test_pi_extension_hooks_are_a_real_deploy(self, tmp_path: Path) -> None:
        # Pi hooks ride the safe-git extension WE deploy: active when present,
        # a closable gap (not "local") when absent.
        home = tmp_path / "home"
        rows = {r.capability: r for r in _uniformity(tmp_path / "d", home)}
        assert rows["hooks"].cells["pi"] == "gap"
        ext = home / ".pi" / "agent" / "extensions" / "safe-git.ts"
        ext.parent.mkdir(parents=True)
        ext.write_text("// ext")
        rows = {r.capability: r for r in _uniformity(tmp_path / "d", home)}
        assert rows["hooks"].cells["pi"] == "active"

    def test_native_statusline_is_active(self, tmp_path: Path) -> None:
        rows = {r.capability: r for r in _uniformity(tmp_path / "d", tmp_path / "home")}
        assert rows["statusline"].cells["gemini"] == "active"

    def test_unsupported_capability_is_na(self, tmp_path: Path) -> None:
        rows = {r.capability: r for r in _uniformity(tmp_path / "d", tmp_path / "home")}
        assert rows["statusline"].cells["hermes"] == "na"


# ===========================================================================
# Section 3: Skills
# ===========================================================================


class TestSectionCensuses:
    def _by_vendor(self, dotfiles: Path, home: Path):
        return {c.vendor: c for c in make_service(dotfiles, home).section_censuses()}

    def test_every_skills_vendor_has_a_census(self, tmp_path: Path) -> None:
        by = self._by_vendor(tmp_path / "dotfiles", tmp_path / "home")
        assert set(by) == {"claude", "cursor", "codex", "gemini", "pi", "hermes"}
        assert all(c.deployed == 0 for c in by.values())

    def test_canonical_skills_set_expected(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        seed_skill(dotfiles, "foo")
        seed_skill(dotfiles, "bar")
        by = self._by_vendor(dotfiles, tmp_path / "home")
        assert by["claude"].expected == 2

    def test_deployed_canonical_skills_count_as_ours(self, tmp_path: Path) -> None:
        dotfiles, home = tmp_path / "dotfiles", tmp_path / "home"
        seed_skill(dotfiles, "alpha")
        (home / ".claude" / "skills" / "alpha").mkdir(parents=True)
        by = self._by_vendor(dotfiles, home)
        assert by["claude"].ours == 1
        assert by["claude"].missing == 0

    def test_unknown_deployed_skills_are_foreign_not_drift(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        for name in ("vendor-a", "vendor-b"):
            (home / ".hermes" / "skills" / name).mkdir(parents=True)
        by = self._by_vendor(tmp_path / "dotfiles", home)
        assert by["hermes"].foreign == 2
        assert by["hermes"].missing == 0

    def test_shared_dir_counts_for_codex_and_pi(self, tmp_path: Path) -> None:
        dotfiles, home = tmp_path / "dotfiles", tmp_path / "home"
        seed_skill(dotfiles, "one")
        (home / ".agents" / "skills" / "one").mkdir(parents=True)
        by = self._by_vendor(dotfiles, home)
        assert by["codex"].ours == 1
        assert by["pi"].ours == 1

    def test_files_in_deployed_dir_not_counted(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        skills = home / ".claude" / "skills"
        (skills / "real-skill").mkdir(parents=True)
        (skills / "README.md").write_text("content")
        by = self._by_vendor(tmp_path / "dotfiles", home)
        assert by["claude"].deployed == 1


# ===========================================================================
# Section 4: Subagents
# ===========================================================================


class TestSectionAgents:
    def test_empty_when_no_agents_dir(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path / "dotfiles", tmp_path / "home")
        assert svc.section_agents() == []

    def test_agent_not_deployed_anywhere(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        seed_agent(dotfiles, "researcher")
        rows = make_service(dotfiles, tmp_path / "home").section_agents()
        assert len(rows) == 1
        row = rows[0]
        assert row.label == "researcher"
        assert row.cells.get("claude") is False
        assert row.cells.get("codex") is False
        assert row.cells.get("pi") is False

    def test_agent_deployed_to_claude(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        seed_agent(dotfiles, "coder")
        claude_agents = home / ".claude" / "agents"
        claude_agents.mkdir(parents=True)
        (claude_agents / "coder.md").write_text("# coder")
        rows = make_service(dotfiles, home).section_agents()
        row = rows[0]
        assert row.cells["claude"] is True
        assert row.cells.get("codex") is False

    def test_agent_deployed_to_all_vendors(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        seed_agent(dotfiles, "helper")
        for deploy_path in [
            home / ".claude" / "agents" / "helper.md",
            home / ".codex" / "agents" / "helper.md",
            home / ".pi" / "agent" / "agents" / "helper.md",
        ]:
            deploy_path.parent.mkdir(parents=True, exist_ok=True)
            deploy_path.write_text("# helper")
        rows = make_service(dotfiles, home).section_agents()
        row = rows[0]
        assert row.cells["claude"]
        assert row.cells["codex"]
        assert row.cells["pi"]

    def test_directories_in_agents_dir_skipped(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        sub = dotfiles / "ai" / "subagents" / "not-an-agent"
        sub.mkdir(parents=True)
        rows = make_service(dotfiles, tmp_path / "home").section_agents()
        assert rows == []

    def test_non_md_files_skipped(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        agents_root = dotfiles / "ai" / "subagents"
        agents_root.mkdir(parents=True)
        (agents_root / "README.txt").write_text("ignore me")
        rows = make_service(dotfiles, tmp_path / "home").section_agents()
        assert rows == []

    def test_multiple_agents_sorted(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        for name in ("zebra", "alpha", "middle"):
            seed_agent(dotfiles, name)
        rows = make_service(dotfiles, tmp_path / "home").section_agents()
        names = [r.label for r in rows]
        assert names == sorted(names)


# ===========================================================================
# Section 6: Permissions
# ===========================================================================


class TestSectionPermissions:
    def test_empty_when_no_files(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path / "dotfiles", tmp_path / "home")
        assert svc.section_permissions() == []

    def test_claude_deployed_settings(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        settings = home / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        data = {"permissions": {"allow": ["a", "b", "c"], "deny": ["x"]}}
        settings.write_text(json.dumps(data))
        rows = make_service(tmp_path / "dotfiles", home).section_permissions()
        row = next(r for r in rows if r.label == "Claude Code (deployed)")
        assert row.allow == 3
        assert row.deny == 1

    def test_claude_source_permissions(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        path = dotfiles / "ai" / "agents" / "claude" / "permissions.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"allow": ["a", "b"], "deny": []}))
        rows = make_service(dotfiles, tmp_path / "home").section_permissions()
        row = next(r for r in rows if r.label == "Claude (dotfiles source)")
        assert row.allow == 2
        assert row.deny == 0

    def test_cursor_cli_config(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        path = dotfiles / "ai" / "agents" / "cursor" / "cli-config.json"
        path.parent.mkdir(parents=True)
        data = {"permissions": {"allow": ["Shell(git)"], "deny": ["Shell(rm -rf /)"]}}
        path.write_text(json.dumps(data))
        rows = make_service(dotfiles, tmp_path / "home").section_permissions()
        row = next(r for r in rows if r.label == "Cursor CLI")
        assert row.allow == 1
        assert row.deny == 1

    def test_codex_default_rules_prefix_count(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        path = dotfiles / "ai" / "agents" / "codex" / "default.rules"
        path.parent.mkdir(parents=True)
        path.write_text("prefix_rule allow stuff\nnot a prefix rule\nprefix_rule deny thing\n")
        rows = make_service(dotfiles, tmp_path / "home").section_permissions()
        row = next(r for r in rows if r.label == "Codex (default.rules)")
        assert row.prefix_rules == 2
        assert row.allow == 0

    def test_missing_permissions_key_returns_zero(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        settings = home / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps({}))
        rows = make_service(tmp_path / "dotfiles", home).section_permissions()
        row = next(r for r in rows if r.label == "Claude Code (deployed)")
        assert row.allow == 0
        assert row.deny == 0

    def test_all_sources_present(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        settings = home / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps({"permissions": {"allow": ["x"], "deny": []}}))
        perm = dotfiles / "ai" / "agents" / "claude" / "permissions.json"
        perm.parent.mkdir(parents=True)
        perm.write_text(json.dumps({"allow": [], "deny": ["y"]}))
        cursor = dotfiles / "ai" / "agents" / "cursor" / "cli-config.json"
        cursor.parent.mkdir(parents=True)
        cursor.write_text(json.dumps({"permissions": {"allow": ["z"], "deny": []}}))
        rules = dotfiles / "ai" / "agents" / "codex" / "default.rules"
        rules.parent.mkdir(parents=True)
        rules.write_text("prefix_rule foo\n")
        rows = make_service(dotfiles, home).section_permissions()
        labels = {r.label for r in rows}
        assert labels == {
            "Claude Code (deployed)",
            "Claude (dotfiles source)",
            "Cursor CLI",
            "Codex (default.rules)",
        }


# ===========================================================================
# Aggregator: overview()
# ===========================================================================


class TestOverviewAggregator:
    def test_returns_agent_overview_instance(self, tmp_path: Path) -> None:
        result = make_service(tmp_path / "dotfiles", tmp_path / "home").overview()
        assert isinstance(result, AgentOverview)

    def test_overview_is_frozen(self, tmp_path: Path) -> None:
        result = make_service(tmp_path / "dotfiles", tmp_path / "home").overview()
        with pytest.raises(Exception, match="frozen"):
            result.mcp = ()  # type: ignore[misc]

    def test_full_overview_aggregates_all_sections(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        # Seed one item per section
        _seed_mcp_config(home, ".claude.json", ["srv"])
        seed_claude_hooks(dotfiles, {"Stop": []})
        seed_skill(dotfiles, "my-skill")
        seed_agent(dotfiles, "my-agent")
        seed_rule(dotfiles, "my-rule")
        settings = home / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps({"permissions": {"allow": ["a"], "deny": []}}))

        result = make_service(dotfiles, home).overview()
        assert len(result.mcp) == 1
        assert len(result.hooks) == 4  # one row per hook intent
        assert {c.vendor for c in result.censuses} >= {"claude", "hermes"}
        assert next(c for c in result.censuses if c.vendor == "claude").expected == 1
        assert len(result.agents) == 1
        assert len(result.permissions) == 1
        assert len(result.uniformity) == 6
        assert result.vendor_surfaces  # the per-vendor pages ride the same fleet


# ===========================================================================
# Agent surfaces (folded into overview)
# ===========================================================================


def _surfaces_of(dotfiles: Path, home: Path) -> list[AgentSurface]:
    return list(make_service(dotfiles, home).overview().vendor_surfaces)


class TestAgentSurfaces:
    def test_vendor_surfaces_returns_vendor_surface_rows(self, tmp_path: Path) -> None:
        surfaces = _surfaces_of(tmp_path / "dotfiles", tmp_path / "home")
        assert all(isinstance(s, AgentSurface) for s in surfaces)
        assert {s.agent for s in surfaces} == {
            "claude",
            "cursor",
            "codex",
            "gemini",
            "pi",
            "hermes",
        }

    def test_present_path_has_present_status(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        settings = home / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text("{}")
        surfaces = _surfaces_of(tmp_path / "dotfiles", home)
        settings_row = next(
            (s for s in surfaces if s.agent == "claude" and s.label == "settings"),
            None,
        )
        assert settings_row is not None
        assert settings_row.status == "present"

    def test_missing_path_has_missing_status(self, tmp_path: Path) -> None:
        surfaces = _surfaces_of(tmp_path / "dotfiles", tmp_path / "home")
        claude_surfaces = [s for s in surfaces if s.agent == "claude"]
        assert all(s.status == "missing" for s in claude_surfaces)

    def test_gemini_shows_uniform_checklist_with_reasoned_na_rows(self, tmp_path: Path) -> None:
        # Every agent gets the same checklist; gemini's local-only rows carry a reason.
        surfaces = _surfaces_of(tmp_path / "dotfiles", tmp_path / "home")
        gemini = [s for s in surfaces if s.agent == "gemini"]
        assert len(gemini) > 1
        subagents = next(s for s in gemini if s.label == "subagents")
        assert subagents.status == "skipped"
        assert subagents.detail  # never a bare, unexplained n/a

    def test_overview_vendor_surfaces_populated(self, tmp_path: Path) -> None:
        result = make_service(tmp_path / "dotfiles", tmp_path / "home").overview()
        assert isinstance(result.vendor_surfaces, tuple)
        assert len(result.vendor_surfaces) > 0


# ---------------------------------------------------------------------------
# Plugins — drift against the plugins.yaml allowlist
# ---------------------------------------------------------------------------


def _seed_plugins(dotfiles: Path, home: Path, *, declared: list[str], installed: list[str]) -> None:
    yaml_path = dotfiles / "ai" / "agents" / "claude" / "plugins.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text("\n".join(f"- {name}" for name in declared) + "\n")
    cfg = home / ".claude" / "plugins" / "installed_plugins.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        json.dumps(
            {"plugins": {f"{n}@claude-plugins-official": [{"version": "1.0"}] for n in installed}}
        )
    )


def test_plugins_flag_undeclared_drift(tmp_path: Path) -> None:
    dotfiles, home = tmp_path / "dotfiles", tmp_path / "home"
    _seed_plugins(dotfiles, home, declared=["superpowers"], installed=["superpowers", "notion"])
    rows = {p.name: p for p in make_service(dotfiles, home).section_plugins()}
    assert rows["superpowers"].declared is True
    assert rows["notion"].declared is False


def test_plugins_all_declared_when_allowlist_matches(tmp_path: Path) -> None:
    dotfiles, home = tmp_path / "dotfiles", tmp_path / "home"
    _seed_plugins(dotfiles, home, declared=["superpowers"], installed=["superpowers"])
    assert all(p.declared for p in make_service(dotfiles, home).section_plugins())
