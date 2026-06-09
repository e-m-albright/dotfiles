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


def seed_cursor_hooks(dotfiles: Path, events: list[str]) -> None:
    path = dotfiles / "ai" / "agents" / "cursor" / "hooks" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    hooks = [{"event": e, "command": "cmd"} for e in events]
    path.write_text(json.dumps({"hooks": hooks}))


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
        runner = _runner_codex_mcp("playwright", "granola")

        rows = _service_with_runner(tmp_path / "d", home, runner).section_mcp()
        by = {r.server: r for r in rows}

        assert by["playwright"].claude
        assert by["playwright"].cursor
        assert by["playwright"].codex
        assert by["playwright"].gemini
        assert by["granola"].claude
        assert by["granola"].codex
        assert by["granola"].cursor is False
        assert by["context7"].cursor
        assert by["context7"].claude is False
        # Pi has no MCP surface — always n/a (False), never a failure.
        assert all(r.pi is False for r in rows)

    def test_codex_servers_come_from_the_cli(self, tmp_path: Path) -> None:
        runner = _runner_codex_mcp("playwright")
        rows = _service_with_runner(tmp_path / "d", tmp_path / "home", runner).section_mcp()
        assert [r.server for r in rows] == ["playwright"]
        assert rows[0].codex is True

    def test_codex_cli_failure_degrades_to_empty(self, tmp_path: Path) -> None:
        runner = FakeProcessRunner()
        runner.script(("codex", "mcp", "list"), exit_code=1)
        rows = _service_with_runner(tmp_path / "d", tmp_path / "home", runner).section_mcp()
        assert rows == []


# ===========================================================================
# Section 2: Hooks
# ===========================================================================


class TestSectionHooks:
    def test_empty_when_no_hook_files(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path / "dotfiles", tmp_path / "home")
        assert svc.section_hooks() == []

    def test_union_of_events_sorted(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        seed_claude_hooks(dotfiles, {"Stop": [], "PreToolUse": []})
        seed_cursor_hooks(dotfiles, ["afterFileEdit"])
        rows = make_service(dotfiles, tmp_path / "home").section_hooks()
        events = [r.event for r in rows]
        assert events == sorted(events)
        assert set(events) == {"Stop", "PreToolUse", "afterFileEdit"}

    def test_claude_flag_set_only_for_claude_events(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        seed_claude_hooks(dotfiles, {"Stop": []})
        seed_cursor_hooks(dotfiles, ["afterFileEdit"])
        rows = make_service(dotfiles, tmp_path / "home").section_hooks()
        stop_row = next(r for r in rows if r.event == "Stop")
        after_row = next(r for r in rows if r.event == "afterFileEdit")
        assert stop_row.claude is True
        assert stop_row.cursor is False
        assert after_row.claude is False
        assert after_row.cursor is True

    def test_codex_events_included(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        seed_codex_hooks(dotfiles, {"PostToolUse": [], "Stop": []})
        rows = make_service(dotfiles, tmp_path / "home").section_hooks()
        events = {r.event for r in rows}
        assert "PostToolUse" in events
        stop_row = next(r for r in rows if r.event == "Stop")
        assert stop_row.codex is True
        assert stop_row.claude is False

    def test_shared_event_across_all_three_vendors(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        seed_claude_hooks(dotfiles, {"Stop": []})
        seed_cursor_hooks(dotfiles, ["Stop"])
        seed_codex_hooks(dotfiles, {"Stop": []})
        rows = make_service(dotfiles, tmp_path / "home").section_hooks()
        assert len(rows) == 1
        row = rows[0]
        assert row.event == "Stop"
        assert row.claude
        assert row.cursor
        assert row.codex

    def test_invalid_json_graceful(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        path = dotfiles / "ai" / "agents" / "claude" / "hooks.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("BAD")
        assert make_service(dotfiles, tmp_path / "home").section_hooks() == []


# ===========================================================================
# Section 3: Skills
# ===========================================================================


class TestSectionSkills:
    def test_zero_when_no_dirs(self, tmp_path: Path) -> None:
        summary = make_service(tmp_path / "dotfiles", tmp_path / "home").section_skills()
        assert summary.canonical_skills == 0
        assert summary.claude_deployed == 0
        assert summary.shared_deployed == 0

    def test_counts_skill_md_files(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        seed_skill(dotfiles, "foo")
        seed_skill(dotfiles, "bar")
        summary = make_service(dotfiles, tmp_path / "home").section_skills()
        assert summary.canonical_skills == 2

    def test_dir_without_skill_md_not_counted(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        empty_dir = dotfiles / "ai" / "skills" / "empty-skill"
        empty_dir.mkdir(parents=True)
        summary = make_service(dotfiles, tmp_path / "home").section_skills()
        assert summary.canonical_skills == 0

    def test_claude_deployed_count(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        claude_skills = home / ".claude" / "skills"
        for name in ("alpha", "beta", "gamma"):
            (claude_skills / name).mkdir(parents=True)
        summary = make_service(tmp_path / "dotfiles", home).section_skills()
        assert summary.claude_deployed == 3

    def test_shared_deployed_count(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        shared = home / ".agents" / "skills"
        (shared / "one").mkdir(parents=True)
        (shared / "two").mkdir(parents=True)
        summary = make_service(tmp_path / "dotfiles", home).section_skills()
        assert summary.shared_deployed == 2

    def test_files_in_deployed_dir_not_counted(self, tmp_path: Path) -> None:
        """Only subdirectories count; plain files are ignored."""
        home = tmp_path / "home"
        claude_skills = home / ".claude" / "skills"
        (claude_skills / "real-skill").mkdir(parents=True)
        (claude_skills / "README.md").write_text("content")
        summary = make_service(tmp_path / "dotfiles", home).section_skills()
        assert summary.claude_deployed == 1


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
        assert row.name == "researcher"
        assert row.claude is False
        assert row.codex is False
        assert row.pi is False

    def test_agent_deployed_to_claude(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        home = tmp_path / "home"
        seed_agent(dotfiles, "coder")
        claude_agents = home / ".claude" / "agents"
        claude_agents.mkdir(parents=True)
        (claude_agents / "coder.md").write_text("# coder")
        rows = make_service(dotfiles, home).section_agents()
        row = rows[0]
        assert row.claude is True
        assert row.codex is False

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
        assert row.claude
        assert row.codex
        assert row.pi

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
        names = [r.name for r in rows]
        assert names == sorted(names)


# ===========================================================================
# Section 5: Rules
# ===========================================================================


class TestSectionRules:
    def test_zero_when_dirs_missing(self, tmp_path: Path) -> None:
        summary = make_service(tmp_path / "dotfiles", tmp_path / "home").section_rules()
        assert summary.canonical_rules == 0
        assert summary.claude_deployed == 0
        assert summary.cursor_deployed == 0

    def test_counts_mdc_files_in_process_dir(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        seed_rule(dotfiles, "process-safety")
        seed_rule(dotfiles, "commit-style")
        summary = make_service(dotfiles, tmp_path / "home").section_rules()
        assert summary.canonical_rules == 2

    def test_non_mdc_not_counted_as_canonical(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        rules_root = dotfiles / "ai" / "rules" / "process"
        rules_root.mkdir(parents=True)
        (rules_root / "README.md").write_text("docs")
        summary = make_service(dotfiles, tmp_path / "home").section_rules()
        assert summary.canonical_rules == 0

    def test_claude_deployed_counts_md_files(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        claude_rules = home / ".claude" / "rules"
        claude_rules.mkdir(parents=True)
        (claude_rules / "a.md").write_text("rule a")
        (claude_rules / "b.md").write_text("rule b")
        summary = make_service(tmp_path / "dotfiles", home).section_rules()
        assert summary.claude_deployed == 2

    def test_cursor_deployed_counts_mdc_entries(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        cursor_rules = dotfiles / "ai" / "agents" / "cursor" / "rules"
        cursor_rules.mkdir(parents=True)
        # Create real symlinks pointing to source files
        src1 = dotfiles / "ai" / "rules" / "process" / "safety.mdc"
        src1.parent.mkdir(parents=True, exist_ok=True)
        src1.write_text("# safety")
        src2 = dotfiles / "ai" / "rules" / "process" / "style.mdc"
        src2.write_text("# style")
        (cursor_rules / "safety.mdc").symlink_to(src1)
        (cursor_rules / "style.mdc").symlink_to(src2)
        summary = make_service(dotfiles, tmp_path / "home").section_rules()
        assert summary.cursor_deployed == 2

    def test_non_mdc_in_cursor_rules_not_counted(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        cursor_rules = dotfiles / "ai" / "agents" / "cursor" / "rules"
        cursor_rules.mkdir(parents=True)
        (cursor_rules / "README.md").write_text("docs")
        summary = make_service(dotfiles, tmp_path / "home").section_rules()
        assert summary.cursor_deployed == 0


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
        assert len(result.hooks) == 1
        assert result.skills.canonical_skills == 1
        assert len(result.agents) == 1
        assert result.rules.canonical_rules == 1
        assert len(result.permissions) == 1


# ===========================================================================
# Agent surfaces (folded into overview)
# ===========================================================================


class TestAgentSurfaces:
    def test_vendor_surfaces_returns_list_of_vendor_surface(self, tmp_path: Path) -> None:
        svc = make_service(tmp_path / "dotfiles", tmp_path / "home")
        surfaces = svc.vendor_surfaces()
        assert isinstance(surfaces, list)
        assert all(isinstance(s, AgentSurface) for s in surfaces)

    def test_surfaces_include_claude_entries(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude" / "skills").mkdir(parents=True)
        (home / ".claude.json").parent.mkdir(parents=True, exist_ok=True)
        (home / ".claude.json").write_text("{}")
        surfaces = make_service(tmp_path / "dotfiles", home).vendor_surfaces()
        vendors = {s.agent for s in surfaces}
        assert "claude" in vendors

    def test_present_path_has_present_status(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        settings = home / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text("{}")
        surfaces = make_service(tmp_path / "dotfiles", home).vendor_surfaces()
        settings_row = next(
            (s for s in surfaces if s.agent == "claude" and s.label == "settings"),
            None,
        )
        assert settings_row is not None
        assert settings_row.status == "present"

    def test_missing_path_has_missing_status(self, tmp_path: Path) -> None:
        surfaces = make_service(tmp_path / "dotfiles", tmp_path / "home").vendor_surfaces()
        claude_surfaces = [s for s in surfaces if s.agent == "claude"]
        assert all(s.status == "missing" for s in claude_surfaces)

    def test_gemini_shows_uniform_checklist_with_na_rows(self, tmp_path: Path) -> None:
        # Every agent gets the same checklist; Gemini's no-such-surface rows are n/a.
        surfaces = make_service(tmp_path / "dotfiles", tmp_path / "home").vendor_surfaces()
        gemini = [s for s in surfaces if s.agent == "gemini"]
        assert len(gemini) > 1
        skills = next(s for s in gemini if s.label == "skills")
        assert skills.status == "skipped"  # gemini has no skills surface → n/a

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
