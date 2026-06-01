"""Tests for AgentOverviewService — all sections, no real filesystem."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dotfiles.core.agent_overview import AgentOverviewService
from dotfiles.core.models import AgentOverview, VendorSurface
from tests.fakes import FakeFileSystem, FakeProcessRunner

DOTFILES = Path("/dotfiles")
HOME = Path("/home/evan")


def make_service(fs: FakeFileSystem) -> AgentOverviewService:
    return AgentOverviewService(
        fs=fs,
        runner=FakeProcessRunner(),
        dotfiles_dir=DOTFILES,
        home=HOME,
    )


def make_service_with_which(fs: FakeFileSystem, which: dict[str, str]) -> AgentOverviewService:
    """Build service with a scripted which() for CLI-gated vendor checks."""
    return AgentOverviewService(
        fs=fs,
        runner=FakeProcessRunner(),
        dotfiles_dir=DOTFILES,
        home=HOME,
        which=which.get,
    )


# ---------------------------------------------------------------------------
# Helpers to seed filesystem
# ---------------------------------------------------------------------------


def seed_mcp(fs: FakeFileSystem, servers: dict) -> None:
    path = DOTFILES / "agents" / "shared" / "mcp-servers.json"
    fs.write_text(path, json.dumps(servers))


def seed_claude_hooks(fs: FakeFileSystem, hooks_dict: dict) -> None:
    path = DOTFILES / "agents" / "claude" / "hooks.json"
    fs.write_text(path, json.dumps({"hooks": hooks_dict}))


def seed_cursor_hooks(fs: FakeFileSystem, events: list[str]) -> None:
    path = DOTFILES / "agents" / "cursor" / "hooks" / "hooks.json"
    hooks = [{"event": e, "command": "cmd"} for e in events]
    fs.write_text(path, json.dumps({"hooks": hooks}))


def seed_codex_hooks(fs: FakeFileSystem, hooks_dict: dict) -> None:
    path = DOTFILES / "agents" / "codex" / "hooks.json"
    fs.write_text(path, json.dumps({"hooks": hooks_dict}))


def seed_skill(fs: FakeFileSystem, name: str) -> None:
    skill_dir = DOTFILES / ".ai" / "skills" / name
    fs.mkdir(skill_dir)
    skill_root = DOTFILES / ".ai" / "skills"
    fs.mkdir(skill_root)
    fs.write_text(skill_dir / "SKILL.md", f"# {name}")


def seed_agent(fs: FakeFileSystem, name: str) -> None:
    agents_root = DOTFILES / ".ai" / "agents"
    fs.mkdir(agents_root)
    fs.write_text(agents_root / f"{name}.md", f"# {name}")


def seed_rule(fs: FakeFileSystem, name: str) -> None:
    rules_root = DOTFILES / ".ai" / "rules" / "process"
    fs.mkdir(rules_root)
    fs.write_text(rules_root / f"{name}.mdc", f"# {name}")


# ===========================================================================
# Section 1: MCP Servers
# ===========================================================================


class TestSectionMcp:
    def test_empty_when_file_missing(self) -> None:
        fs = FakeFileSystem()
        svc = make_service(fs)
        assert svc.section_mcp() == []

    def test_skips_non_object_entries(self) -> None:
        fs = FakeFileSystem()
        seed_mcp(fs, {"$comment": "ignore me", "myserver": {"targets": ["claude"]}})
        rows = make_service(fs).section_mcp()
        assert len(rows) == 1
        assert rows[0].server == "myserver"

    def test_claude_cursor_flags(self) -> None:
        fs = FakeFileSystem()
        seed_mcp(
            fs,
            {
                "alpha": {"targets": ["claude", "cursor"]},
                "beta": {"targets": ["codex", "gemini"]},
            },
        )
        svc = make_service(fs)
        rows = svc.section_mcp()
        alpha = next(r for r in rows if r.server == "alpha")
        beta = next(r for r in rows if r.server == "beta")

        assert alpha.claude is True
        assert alpha.cursor is True
        assert alpha.codex is False
        assert alpha.gemini is False

        assert beta.claude is False
        assert beta.cursor is False
        assert beta.codex is True
        assert beta.gemini is True

    def test_all_four_vendors(self) -> None:
        fs = FakeFileSystem()
        seed_mcp(fs, {"full": {"targets": ["claude", "cursor", "codex", "gemini"]}})
        row = make_service(fs).section_mcp()[0]
        assert row.claude
        assert row.cursor
        assert row.codex
        assert row.gemini

    def test_no_targets_key(self) -> None:
        fs = FakeFileSystem()
        seed_mcp(fs, {"srv": {}})
        rows = make_service(fs).section_mcp()
        assert len(rows) == 1
        assert rows[0].claude is False

    def test_invalid_json_returns_empty(self) -> None:
        fs = FakeFileSystem()
        path = DOTFILES / "agents" / "shared" / "mcp-servers.json"
        fs.write_text(path, "NOT JSON")
        assert make_service(fs).section_mcp() == []


# ===========================================================================
# Section 2: Hooks
# ===========================================================================


class TestSectionHooks:
    def test_empty_when_no_hook_files(self) -> None:
        fs = FakeFileSystem()
        assert make_service(fs).section_hooks() == []

    def test_union_of_events_sorted(self) -> None:
        fs = FakeFileSystem()
        seed_claude_hooks(fs, {"Stop": [], "PreToolUse": []})
        seed_cursor_hooks(fs, ["afterFileEdit"])
        rows = make_service(fs).section_hooks()
        events = [r.event for r in rows]
        assert events == sorted(events)
        assert set(events) == {"Stop", "PreToolUse", "afterFileEdit"}

    def test_claude_flag_set_only_for_claude_events(self) -> None:
        fs = FakeFileSystem()
        seed_claude_hooks(fs, {"Stop": []})
        seed_cursor_hooks(fs, ["afterFileEdit"])
        rows = make_service(fs).section_hooks()
        stop_row = next(r for r in rows if r.event == "Stop")
        after_row = next(r for r in rows if r.event == "afterFileEdit")
        assert stop_row.claude is True
        assert stop_row.cursor is False
        assert after_row.claude is False
        assert after_row.cursor is True

    def test_codex_events_included(self) -> None:
        fs = FakeFileSystem()
        seed_codex_hooks(fs, {"PostToolUse": [], "Stop": []})
        rows = make_service(fs).section_hooks()
        events = {r.event for r in rows}
        assert "PostToolUse" in events
        stop_row = next(r for r in rows if r.event == "Stop")
        assert stop_row.codex is True
        assert stop_row.claude is False

    def test_shared_event_across_all_three_vendors(self) -> None:
        fs = FakeFileSystem()
        seed_claude_hooks(fs, {"Stop": []})
        seed_cursor_hooks(fs, ["Stop"])
        seed_codex_hooks(fs, {"Stop": []})
        rows = make_service(fs).section_hooks()
        assert len(rows) == 1
        row = rows[0]
        assert row.event == "Stop"
        assert row.claude
        assert row.cursor
        assert row.codex

    def test_invalid_json_graceful(self) -> None:
        fs = FakeFileSystem()
        path = DOTFILES / "agents" / "claude" / "hooks.json"
        fs.write_text(path, "BAD")
        assert make_service(fs).section_hooks() == []


# ===========================================================================
# Section 3: Skills
# ===========================================================================


class TestSectionSkills:
    def test_zero_when_no_dirs(self) -> None:
        fs = FakeFileSystem()
        summary = make_service(fs).section_skills()
        assert summary.canonical_skills == 0
        assert summary.claude_deployed == 0
        assert summary.shared_deployed == 0

    def test_counts_skill_md_files(self) -> None:
        fs = FakeFileSystem()
        seed_skill(fs, "foo")
        seed_skill(fs, "bar")
        summary = make_service(fs).section_skills()
        assert summary.canonical_skills == 2

    def test_dir_without_skill_md_not_counted(self) -> None:
        fs = FakeFileSystem()
        skills_root = DOTFILES / ".ai" / "skills"
        fs.mkdir(skills_root)
        empty_dir = skills_root / "empty-skill"
        fs.mkdir(empty_dir)
        summary = make_service(fs).section_skills()
        assert summary.canonical_skills == 0

    def test_claude_deployed_count(self) -> None:
        fs = FakeFileSystem()
        claude_skills = HOME / ".claude" / "skills"
        fs.mkdir(claude_skills)
        for name in ("alpha", "beta", "gamma"):
            d = claude_skills / name
            fs.mkdir(d)
        summary = make_service(fs).section_skills()
        assert summary.claude_deployed == 3

    def test_shared_deployed_count(self) -> None:
        fs = FakeFileSystem()
        shared = HOME / ".agents" / "skills"
        fs.mkdir(shared)
        fs.mkdir(shared / "one")
        fs.mkdir(shared / "two")
        summary = make_service(fs).section_skills()
        assert summary.shared_deployed == 2

    def test_files_in_deployed_dir_not_counted(self) -> None:
        """Only subdirectories count; plain files are ignored."""
        fs = FakeFileSystem()
        claude_skills = HOME / ".claude" / "skills"
        fs.mkdir(claude_skills)
        fs.mkdir(claude_skills / "real-skill")
        fs.write_text(claude_skills / "README.md", "content")
        summary = make_service(fs).section_skills()
        assert summary.claude_deployed == 1


# ===========================================================================
# Section 4: Subagents
# ===========================================================================


class TestSectionAgents:
    def test_empty_when_no_agents_dir(self) -> None:
        fs = FakeFileSystem()
        assert make_service(fs).section_agents() == []

    def test_agent_not_deployed_anywhere(self) -> None:
        fs = FakeFileSystem()
        seed_agent(fs, "researcher")
        rows = make_service(fs).section_agents()
        assert len(rows) == 1
        row = rows[0]
        assert row.name == "researcher"
        assert row.claude is False
        assert row.codex is False
        assert row.pi is False

    def test_agent_deployed_to_claude(self) -> None:
        fs = FakeFileSystem()
        seed_agent(fs, "coder")
        claude_agents = HOME / ".claude" / "agents"
        fs.mkdir(claude_agents)
        fs.write_text(claude_agents / "coder.md", "# coder")
        rows = make_service(fs).section_agents()
        row = rows[0]
        assert row.claude is True
        assert row.codex is False

    def test_agent_deployed_to_all_vendors(self) -> None:
        fs = FakeFileSystem()
        seed_agent(fs, "helper")
        for deploy_path in [
            HOME / ".claude" / "agents" / "helper.md",
            HOME / ".codex" / "agents" / "helper.md",
            HOME / ".pi" / "agent" / "agents" / "helper.md",
        ]:
            fs.write_text(deploy_path, "# helper")
        rows = make_service(fs).section_agents()
        row = rows[0]
        assert row.claude
        assert row.codex
        assert row.pi

    def test_directories_in_agents_dir_skipped(self) -> None:
        fs = FakeFileSystem()
        agents_root = DOTFILES / ".ai" / "agents"
        fs.mkdir(agents_root)
        sub = agents_root / "not-an-agent"
        fs.mkdir(sub)
        rows = make_service(fs).section_agents()
        assert rows == []

    def test_non_md_files_skipped(self) -> None:
        fs = FakeFileSystem()
        agents_root = DOTFILES / ".ai" / "agents"
        fs.mkdir(agents_root)
        fs.write_text(agents_root / "README.txt", "ignore me")
        rows = make_service(fs).section_agents()
        assert rows == []

    def test_multiple_agents_sorted(self) -> None:
        fs = FakeFileSystem()
        for name in ("zebra", "alpha", "middle"):
            seed_agent(fs, name)
        rows = make_service(fs).section_agents()
        names = [r.name for r in rows]
        assert names == sorted(names)


# ===========================================================================
# Section 5: Rules
# ===========================================================================


class TestSectionRules:
    def test_zero_when_dirs_missing(self) -> None:
        fs = FakeFileSystem()
        summary = make_service(fs).section_rules()
        assert summary.canonical_rules == 0
        assert summary.claude_deployed == 0
        assert summary.cursor_deployed == 0

    def test_counts_mdc_files_in_process_dir(self) -> None:
        fs = FakeFileSystem()
        seed_rule(fs, "process-safety")
        seed_rule(fs, "commit-style")
        summary = make_service(fs).section_rules()
        assert summary.canonical_rules == 2

    def test_non_mdc_not_counted_as_canonical(self) -> None:
        fs = FakeFileSystem()
        rules_root = DOTFILES / ".ai" / "rules" / "process"
        fs.mkdir(rules_root)
        fs.write_text(rules_root / "README.md", "docs")
        summary = make_service(fs).section_rules()
        assert summary.canonical_rules == 0

    def test_claude_deployed_counts_md_files(self) -> None:
        fs = FakeFileSystem()
        claude_rules = HOME / ".claude" / "rules"
        fs.mkdir(claude_rules)
        fs.write_text(claude_rules / "a.md", "rule a")
        fs.write_text(claude_rules / "b.md", "rule b")
        summary = make_service(fs).section_rules()
        assert summary.claude_deployed == 2

    def test_cursor_deployed_counts_mdc_entries(self) -> None:
        fs = FakeFileSystem()
        cursor_rules = DOTFILES / "agents" / "cursor" / "rules"
        fs.mkdir(cursor_rules)
        # Simulate symlinks via is_symlink (FakeFileSystem supports it)
        fs.symlink(
            DOTFILES / ".ai" / "rules" / "process" / "safety.mdc",
            cursor_rules / "safety.mdc",
        )
        fs.symlink(
            DOTFILES / ".ai" / "rules" / "process" / "style.mdc",
            cursor_rules / "style.mdc",
        )
        summary = make_service(fs).section_rules()
        assert summary.cursor_deployed == 2

    def test_non_mdc_in_cursor_rules_not_counted(self) -> None:
        fs = FakeFileSystem()
        cursor_rules = DOTFILES / "agents" / "cursor" / "rules"
        fs.mkdir(cursor_rules)
        fs.write_text(cursor_rules / "README.md", "docs")
        summary = make_service(fs).section_rules()
        assert summary.cursor_deployed == 0


# ===========================================================================
# Section 6: Permissions
# ===========================================================================


class TestSectionPermissions:
    def test_empty_when_no_files(self) -> None:
        fs = FakeFileSystem()
        assert make_service(fs).section_permissions() == []

    def test_claude_deployed_settings(self) -> None:
        fs = FakeFileSystem()
        data = {"permissions": {"allow": ["a", "b", "c"], "deny": ["x"]}}
        fs.write_text(HOME / ".claude" / "settings.json", json.dumps(data))
        rows = make_service(fs).section_permissions()
        row = next(r for r in rows if r.label == "Claude Code (deployed)")
        assert row.allow == 3
        assert row.deny == 1

    def test_claude_source_permissions(self) -> None:
        fs = FakeFileSystem()
        data = {"allow": ["a", "b"], "deny": []}
        fs.write_text(DOTFILES / "agents" / "claude" / "permissions.json", json.dumps(data))
        rows = make_service(fs).section_permissions()
        row = next(r for r in rows if r.label == "Claude (dotfiles source)")
        assert row.allow == 2
        assert row.deny == 0

    def test_cursor_cli_config(self) -> None:
        fs = FakeFileSystem()
        data = {"permissions": {"allow": ["Shell(git)"], "deny": ["Shell(rm -rf /)"]}}
        fs.write_text(DOTFILES / "agents" / "cursor" / "cli-config.json", json.dumps(data))
        rows = make_service(fs).section_permissions()
        row = next(r for r in rows if r.label == "Cursor CLI")
        assert row.allow == 1
        assert row.deny == 1

    def test_codex_default_rules_prefix_count(self) -> None:
        fs = FakeFileSystem()
        rules_text = "prefix_rule allow stuff\nnot a prefix rule\nprefix_rule deny thing\n"
        fs.write_text(DOTFILES / "agents" / "codex" / "default.rules", rules_text)
        rows = make_service(fs).section_permissions()
        row = next(r for r in rows if r.label == "Codex (default.rules)")
        assert row.prefix_rules == 2
        assert row.allow == 0

    def test_missing_permissions_key_returns_zero(self) -> None:
        fs = FakeFileSystem()
        fs.write_text(HOME / ".claude" / "settings.json", json.dumps({}))
        rows = make_service(fs).section_permissions()
        row = next(r for r in rows if r.label == "Claude Code (deployed)")
        assert row.allow == 0
        assert row.deny == 0

    def test_all_sources_present(self) -> None:
        fs = FakeFileSystem()
        fs.write_text(
            HOME / ".claude" / "settings.json",
            json.dumps({"permissions": {"allow": ["x"], "deny": []}}),
        )
        fs.write_text(
            DOTFILES / "agents" / "claude" / "permissions.json",
            json.dumps({"allow": [], "deny": ["y"]}),
        )
        fs.write_text(
            DOTFILES / "agents" / "cursor" / "cli-config.json",
            json.dumps({"permissions": {"allow": ["z"], "deny": []}}),
        )
        fs.write_text(
            DOTFILES / "agents" / "codex" / "default.rules",
            "prefix_rule foo\n",
        )
        rows = make_service(fs).section_permissions()
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
    def test_returns_agent_overview_instance(self) -> None:
        fs = FakeFileSystem()
        result = make_service(fs).overview()
        assert isinstance(result, AgentOverview)

    def test_overview_is_frozen(self) -> None:
        fs = FakeFileSystem()
        result = make_service(fs).overview()
        with pytest.raises(Exception, match="frozen"):
            result.mcp = ()  # type: ignore[misc]

    def test_full_overview_aggregates_all_sections(self) -> None:
        fs = FakeFileSystem()
        # Seed one item per section
        seed_mcp(fs, {"srv": {"targets": ["claude"]}})
        seed_claude_hooks(fs, {"Stop": []})
        seed_skill(fs, "my-skill")
        seed_agent(fs, "my-agent")
        seed_rule(fs, "my-rule")
        fs.write_text(
            HOME / ".claude" / "settings.json",
            json.dumps({"permissions": {"allow": ["a"], "deny": []}}),
        )

        result = make_service(fs).overview()
        assert len(result.mcp) == 1
        assert len(result.hooks) == 1
        assert result.skills.canonical_skills == 1
        assert len(result.agents) == 1
        assert result.rules.canonical_rules == 1
        assert len(result.permissions) == 1


# ===========================================================================
# Vendor surfaces (folded into overview)
# ===========================================================================


class TestVendorSurfaces:
    def test_vendor_surfaces_returns_list_of_vendor_surface(self) -> None:
        fs = FakeFileSystem()
        svc = make_service(fs)
        surfaces = svc.vendor_surfaces()
        assert isinstance(surfaces, list)
        assert all(isinstance(s, VendorSurface) for s in surfaces)

    def test_surfaces_include_claude_entries(self) -> None:
        fs = FakeFileSystem()
        # Seed some Claude paths as present
        fs.mkdir(HOME / ".claude" / "skills")
        fs.write_text(HOME / ".claude.json", "{}")
        surfaces = make_service(fs).vendor_surfaces()
        vendors = {s.vendor for s in surfaces}
        assert "claude" in vendors

    def test_present_path_has_present_status(self) -> None:
        fs = FakeFileSystem()
        # ~/.claude/settings.json exists as a file → "present"
        fs.write_text(HOME / ".claude" / "settings.json", "{}")
        surfaces = make_service(fs).vendor_surfaces()
        settings_row = next(
            (s for s in surfaces if s.vendor == "claude" and s.label == "settings.json"),
            None,
        )
        assert settings_row is not None
        assert settings_row.status == "present"

    def test_missing_path_has_missing_status(self) -> None:
        fs = FakeFileSystem()
        surfaces = make_service(fs).vendor_surfaces()
        # Nothing seeded → all claude surfaces missing
        claude_surfaces = [s for s in surfaces if s.vendor == "claude"]
        assert all(s.status == "missing" for s in claude_surfaces)

    def test_gemini_skipped_when_cli_absent(self) -> None:
        fs = FakeFileSystem()
        # Explicitly pass a which() that finds nothing
        svc = make_service_with_which(fs, {})
        surfaces = svc.vendor_surfaces()
        gemini = [s for s in surfaces if s.vendor == "gemini"]
        assert len(gemini) == 1
        assert gemini[0].status == "skipped"

    def test_gemini_checked_when_cli_present(self) -> None:
        fs = FakeFileSystem()
        svc = make_service_with_which(fs, {"gemini": "/usr/local/bin/gemini"})
        surfaces = svc.vendor_surfaces()
        gemini = [s for s in surfaces if s.vendor == "gemini"]
        assert len(gemini) > 1 or gemini[0].status != "skipped"

    def test_overview_vendor_surfaces_populated(self) -> None:
        fs = FakeFileSystem()
        result = make_service(fs).overview()
        # vendor_surfaces should be a non-empty tuple (at minimum claude entries)
        assert isinstance(result.vendor_surfaces, tuple)
        assert len(result.vendor_surfaces) > 0
