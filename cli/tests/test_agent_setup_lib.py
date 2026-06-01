"""Tests for core/agent_setup/lib.py — shared agent-setup helpers.

All tests use tmp_path for home + dotfiles_dir; no real home directory is
touched. FakeProcessRunner is used for all subprocess calls.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dotfiles.core.agent_setup.lib import (
    baked_rule_count,
    build_global_instructions,
    deploy_skills,
    deploy_subagents,
    mcp_servers_for,
    mcp_skip,
    merge_managed_mcp,
    symlink_process_rules,
)
from tests.fakes import FakeProcessRunner, write_tree

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MCP_JSON = """{
  "granola": {
    "type": "http",
    "url": "https://mcp.granola.ai/mcp",
    "targets": ["claude"]
  },
  "playwright": {
    "command": "npx",
    "args": ["-y", "@playwright/mcp@latest"],
    "targets": ["claude", "cursor", "codex"]
  },
  "context7": {
    "type": "http",
    "url": "https://mcp.context7.com/mcp",
    "targets": ["cursor"]
  },
  "_disabled_str": "this is a string sentinel, not an object"
}"""


@pytest.fixture
def dotfiles(tmp_path: Path) -> Path:
    """A minimal dotfiles root with agents/shared/mcp-servers.json."""
    write_tree(
        tmp_path,
        {
            "agents/shared/mcp-servers.json": MCP_JSON,
        },
    )
    return tmp_path


@pytest.fixture
def home(tmp_path: Path) -> Path:
    """A fresh fake home directory."""
    h = tmp_path / "home"
    h.mkdir()
    return h


# ---------------------------------------------------------------------------
# mcp_skip
# ---------------------------------------------------------------------------


class TestMcpSkip:
    def test_empty_when_no_env_no_file(self, home: Path) -> None:
        result = mcp_skip(home, env={})
        assert result == set()

    def test_reads_env_var(self, home: Path) -> None:
        result = mcp_skip(home, env={"MCP_SKIP": "granola,playwright"})
        assert result == {"granola", "playwright"}

    def test_env_strips_whitespace(self, home: Path) -> None:
        result = mcp_skip(home, env={"MCP_SKIP": " granola , playwright "})
        assert result == {"granola", "playwright"}

    def test_reads_skip_file(self, home: Path) -> None:
        skip_file = home / ".config" / "dotfiles" / "mcp-skip"
        skip_file.parent.mkdir(parents=True)
        skip_file.write_text("granola\n# comment\nplaywright\n\n")
        result = mcp_skip(home, env={})
        assert result == {"granola", "playwright"}

    def test_merges_env_and_file(self, home: Path) -> None:
        skip_file = home / ".config" / "dotfiles" / "mcp-skip"
        skip_file.parent.mkdir(parents=True)
        skip_file.write_text("context7\n")
        result = mcp_skip(home, env={"MCP_SKIP": "granola"})
        assert result == {"granola", "context7"}

    def test_ignores_comment_lines_in_file(self, home: Path) -> None:
        skip_file = home / ".config" / "dotfiles" / "mcp-skip"
        skip_file.parent.mkdir(parents=True)
        skip_file.write_text("# this is a comment\ngranola\n")
        result = mcp_skip(home, env={})
        assert result == {"granola"}

    def test_ignores_blank_lines_in_file(self, home: Path) -> None:
        skip_file = home / ".config" / "dotfiles" / "mcp-skip"
        skip_file.parent.mkdir(parents=True)
        skip_file.write_text("\n\ngranola\n\n")
        result = mcp_skip(home, env={})
        assert result == {"granola"}


# ---------------------------------------------------------------------------
# mcp_servers_for
# ---------------------------------------------------------------------------


class TestMcpServersFor:
    def test_filters_to_target(self, dotfiles: Path) -> None:
        result = mcp_servers_for(dotfiles, "claude")
        assert set(result.keys()) == {"granola", "playwright"}

    def test_cursor_target(self, dotfiles: Path) -> None:
        result = mcp_servers_for(dotfiles, "cursor")
        assert set(result.keys()) == {"playwright", "context7"}

    def test_codex_target(self, dotfiles: Path) -> None:
        result = mcp_servers_for(dotfiles, "codex")
        assert set(result.keys()) == {"playwright"}

    def test_unknown_target_returns_empty(self, dotfiles: Path) -> None:
        result = mcp_servers_for(dotfiles, "unknown")
        assert result == {}

    def test_targets_key_stripped(self, dotfiles: Path) -> None:
        result = mcp_servers_for(dotfiles, "claude")
        for cfg in result.values():
            assert "targets" not in cfg

    def test_other_fields_preserved(self, dotfiles: Path) -> None:
        result = mcp_servers_for(dotfiles, "claude")
        assert result["granola"]["url"] == "https://mcp.granola.ai/mcp"
        assert result["playwright"]["command"] == "npx"
        assert result["playwright"]["args"] == ["-y", "@playwright/mcp@latest"]

    def test_skip_excludes_names(self, dotfiles: Path) -> None:
        result = mcp_servers_for(dotfiles, "claude", skip={"granola"})
        assert "granola" not in result
        assert "playwright" in result

    def test_skip_all(self, dotfiles: Path) -> None:
        result = mcp_servers_for(dotfiles, "claude", skip={"granola", "playwright"})
        assert result == {}

    def test_missing_json_returns_empty(self, tmp_path: Path) -> None:
        result = mcp_servers_for(tmp_path, "claude")
        assert result == {}

    def test_string_sentinel_entries_excluded(self, dotfiles: Path) -> None:
        # _disabled_str is a string, not an object — must not appear
        result = mcp_servers_for(dotfiles, "claude")
        assert "_disabled_str" not in result


# ---------------------------------------------------------------------------
# deploy_subagents
# ---------------------------------------------------------------------------


class TestDeploySubagents:
    def test_copies_agents(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        write_tree(
            dotfiles,
            {
                ".ai/agents/debugger.md": "# Debugger",
                ".ai/agents/reviewer.md": "# Reviewer",
            },
        )
        dest = tmp_path / "dest"
        results = deploy_subagents(dotfiles, dest)

        assert len(results) == 2
        assert all(r.ok for r in results)
        assert (dest / "debugger.md").read_text() == "# Debugger"
        assert (dest / "reviewer.md").read_text() == "# Reviewer"

    def test_creates_dest_dir(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        write_tree(dotfiles, {".ai/agents/a.md": "x"})
        dest = tmp_path / "new" / "nested" / "dest"
        deploy_subagents(dotfiles, dest)
        assert dest.is_dir()

    def test_missing_agents_dir_returns_empty(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        dotfiles.mkdir()
        dest = tmp_path / "dest"
        results = deploy_subagents(dotfiles, dest)
        assert results == []

    def test_only_md_files_copied(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        write_tree(
            dotfiles,
            {
                ".ai/agents/agent.md": "# Agent",
                ".ai/agents/ignore.txt": "not an agent",
            },
        )
        dest = tmp_path / "dest"
        results = deploy_subagents(dotfiles, dest)
        assert len(results) == 1
        assert (dest / "agent.md").exists()
        assert not (dest / "ignore.txt").exists()


# ---------------------------------------------------------------------------
# deploy_skills
# ---------------------------------------------------------------------------


class TestDeploySkills:
    def _make_dotfiles(self, tmp_path: Path) -> Path:
        dotfiles = tmp_path / "dotfiles"
        write_tree(
            dotfiles,
            {
                ".ai/skills/my-skill/SKILL.md": "# My Skill",
            },
        )
        return dotfiles

    def test_runs_npx_skills_command(self, tmp_path: Path) -> None:
        dotfiles = self._make_dotfiles(tmp_path)
        runner = FakeProcessRunner()
        result = deploy_skills(runner, dotfiles, "claude-code", which=lambda _: "/usr/bin/npx")

        assert result.ok
        assert len(runner.calls) == 1
        cmd = runner.calls[0]
        assert cmd[0] == "npx"
        assert cmd[1] == "skills"
        assert cmd[2] == "add"
        assert str(dotfiles / ".ai" / "skills") in cmd
        assert "-a" in cmd
        assert "claude-code" in cmd
        assert "-g" in cmd
        assert "--copy" in cmd
        assert "-y" in cmd

    def test_error_when_npx_absent(self, tmp_path: Path) -> None:
        dotfiles = self._make_dotfiles(tmp_path)
        runner = FakeProcessRunner()
        result = deploy_skills(runner, dotfiles, "claude-code", which=lambda _: None)

        assert not result.ok
        assert "npx" in result.message.lower()
        assert len(runner.calls) == 0

    def test_error_when_skills_dir_missing(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        dotfiles.mkdir()
        runner = FakeProcessRunner()
        result = deploy_skills(runner, dotfiles, "claude-code", which=lambda _: "/usr/bin/npx")

        assert not result.ok
        assert len(runner.calls) == 0

    def test_failure_exit_code_returns_error(self, tmp_path: Path) -> None:
        dotfiles = self._make_dotfiles(tmp_path)
        runner = FakeProcessRunner()
        runner.script(
            (
                "npx",
                "skills",
                "add",
                str(dotfiles / ".ai" / "skills"),
                "-s",
                "*",
                "-a",
                "codex",
                "-g",
                "-y",
                "--copy",
            ),
            exit_code=1,
            stderr="some error",
        )
        result = deploy_skills(runner, dotfiles, "codex", which=lambda _: "/usr/bin/npx")

        assert not result.ok
        assert "Failed" in result.message


# ---------------------------------------------------------------------------
# symlink_process_rules
# ---------------------------------------------------------------------------

RULE_WITH_FRONTMATTER = """\
---
description: A test rule
alwaysApply: true
---

# Rule Body

Some content here.
"""


class TestSymlinkProcessRules:
    def _make_dotfiles(self, tmp_path: Path, rules: dict[str, str] | None = None) -> Path:
        dotfiles = tmp_path / "dotfiles"
        default_rules = (
            rules if rules is not None else {"global-process.mdc": RULE_WITH_FRONTMATTER}
        )
        tree: dict[str, str | None] = {
            f".ai/rules/process/{name}": content for name, content in default_rules.items()
        }
        write_tree(dotfiles, tree)
        return dotfiles

    def test_creates_symlinks_with_suffix(self, tmp_path: Path) -> None:
        dotfiles = self._make_dotfiles(tmp_path, {"rule-a.mdc": "x", "rule-b.mdc": "y"})
        dest = tmp_path / "dest"
        results = symlink_process_rules(dotfiles, dest, ".md")

        assert len(results) == 2
        assert all(r.ok for r in results)
        assert (dest / "rule-a.md").is_symlink()
        assert (dest / "rule-b.md").is_symlink()
        assert not (dest / "rule-a.mdc").exists()

    def test_symlink_points_to_source(self, tmp_path: Path) -> None:
        dotfiles = self._make_dotfiles(tmp_path)
        dest = tmp_path / "dest"
        symlink_process_rules(dotfiles, dest, ".md")

        link = dest / "global-process.md"
        assert link.is_symlink()
        assert (
            link.resolve()
            == (dotfiles / ".ai" / "rules" / "process" / "global-process.mdc").resolve()
        )

    def test_mdc_suffix(self, tmp_path: Path) -> None:
        dotfiles = self._make_dotfiles(tmp_path)
        dest = tmp_path / "dest"
        symlink_process_rules(dotfiles, dest, ".mdc")

        assert (dest / "global-process.mdc").is_symlink()
        assert not (dest / "global-process.md").exists()

    def test_cleans_stale_other_suffix(self, tmp_path: Path) -> None:
        """Switching from .mdc to .md should remove the old .mdc symlink."""
        dotfiles = self._make_dotfiles(tmp_path)
        dest = tmp_path / "dest"
        # First deploy with .mdc
        symlink_process_rules(dotfiles, dest, ".mdc")
        assert (dest / "global-process.mdc").is_symlink()
        # Now switch to .md — old .mdc should be cleaned up
        symlink_process_rules(dotfiles, dest, ".md")
        assert (dest / "global-process.md").is_symlink()
        assert not (dest / "global-process.mdc").exists()

    def test_idempotent(self, tmp_path: Path) -> None:
        dotfiles = self._make_dotfiles(tmp_path)
        dest = tmp_path / "dest"
        symlink_process_rules(dotfiles, dest, ".md")
        symlink_process_rules(dotfiles, dest, ".md")  # second call should not raise
        assert (dest / "global-process.md").is_symlink()

    def test_prunes_orphaned_link_when_rule_retired(self, tmp_path: Path) -> None:
        """Retiring a rule must remove its now-dangling same-suffix symlink."""
        dotfiles = self._make_dotfiles(tmp_path, {"keep.mdc": "x", "retire.mdc": "y"})
        dest = tmp_path / "dest"
        symlink_process_rules(dotfiles, dest, ".md")
        assert (dest / "retire.md").is_symlink()

        # Retire the rule, then re-deploy.
        (dotfiles / ".ai" / "rules" / "process" / "retire.mdc").unlink()
        symlink_process_rules(dotfiles, dest, ".md")

        assert (dest / "keep.md").is_symlink()
        assert not (dest / "retire.md").is_symlink()
        assert "retire.md" not in {p.name for p in dest.iterdir()}

    def test_prune_leaves_unmanaged_files_alone(self, tmp_path: Path) -> None:
        """A user's own file in the rules dir must survive pruning."""
        dotfiles = self._make_dotfiles(tmp_path, {"keep.mdc": "x"})
        dest = tmp_path / "dest"
        dest.mkdir()
        (dest / "my-own.md").write_text("hand-written, not a managed symlink")
        symlink_process_rules(dotfiles, dest, ".md")
        assert (dest / "my-own.md").is_file()
        assert (dest / "keep.md").is_symlink()

    def test_creates_dest_dir(self, tmp_path: Path) -> None:
        dotfiles = self._make_dotfiles(tmp_path)
        dest = tmp_path / "new" / "nested" / "rules"
        symlink_process_rules(dotfiles, dest, ".md")
        assert dest.is_dir()

    def test_missing_process_rules_dir_returns_error(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        dotfiles.mkdir()
        dest = tmp_path / "dest"
        results = symlink_process_rules(dotfiles, dest, ".md")
        assert len(results) == 1
        assert not results[0].ok

    def test_multiple_rules_all_linked(self, tmp_path: Path) -> None:
        rules = {f"rule-{i}.mdc": f"# Rule {i}" for i in range(5)}
        dotfiles = self._make_dotfiles(tmp_path, rules)
        dest = tmp_path / "dest"
        results = symlink_process_rules(dotfiles, dest, ".md")
        assert len(results) == 5
        for i in range(5):
            assert (dest / f"rule-{i}.md").is_symlink()


# ---------------------------------------------------------------------------
# merge_managed_mcp
# ---------------------------------------------------------------------------


class TestMergeManagedMcp:
    def test_servers_win_over_existing(self) -> None:
        out = merge_managed_mcp(
            {"granola": {"url": "old"}},
            {"granola": {"url": "new"}},
            managed_keys={"granola"},
            reset_mcp=False,
        )
        assert out == {"granola": {"url": "new"}}

    def test_unmanaged_existing_entries_preserved(self) -> None:
        out = merge_managed_mcp(
            {"user-added": {"url": "x"}},
            {"granola": {"url": "y"}},
            managed_keys={"granola"},
            reset_mcp=False,
        )
        assert out == {"user-added": {"url": "x"}, "granola": {"url": "y"}}

    def test_reset_purges_stale_managed_keys_only(self) -> None:
        # "old-managed" is managed but no longer in servers → dropped on reset.
        # "user-added" is unmanaged → always kept.
        out = merge_managed_mcp(
            {"old-managed": {"url": "stale"}, "user-added": {"url": "keep"}},
            {"granola": {"url": "new"}},
            managed_keys={"old-managed", "granola"},
            reset_mcp=True,
        )
        assert out == {"user-added": {"url": "keep"}, "granola": {"url": "new"}}

    def test_no_reset_keeps_stale_managed_keys(self) -> None:
        out = merge_managed_mcp(
            {"old-managed": {"url": "stale"}},
            {"granola": {"url": "new"}},
            managed_keys={"old-managed", "granola"},
            reset_mcp=False,
        )
        assert out == {"old-managed": {"url": "stale"}, "granola": {"url": "new"}}


# ---------------------------------------------------------------------------
# build_global_instructions
# ---------------------------------------------------------------------------


class TestBuildGlobalInstructions:
    def _dotfiles(self, tmp_path: Path, rules: dict[str, str] | None = None) -> Path:
        tree: dict[str, str | None] = {"agents/shared/rules.md": "SHARED RULES BODY"}
        for name, body in (rules or {}).items():
            tree[f".ai/rules/process/{name}"] = body
        write_tree(tmp_path, tree)
        return tmp_path

    def test_none_when_rules_md_absent(self, tmp_path: Path) -> None:
        assert build_global_instructions(tmp_path) is None

    def test_header_and_shared_rules_present(self, tmp_path: Path) -> None:
        out = build_global_instructions(self._dotfiles(tmp_path))
        assert out is not None
        assert out.startswith("# Global Agent Instructions\n\nSHARED RULES BODY\n")

    def test_extra_sections_land_between_rules_and_baked(self, tmp_path: Path) -> None:
        dotfiles = self._dotfiles(tmp_path, {"a.mdc": "---\ndescription: x\n---\nRULE A BODY"})
        out = build_global_instructions(
            dotfiles, extra_sections=("## Vendor-Specific", "", "- note")
        )
        assert out is not None
        assert "## Vendor-Specific\n\n- note" in out
        # extra section appears before the baked rules block
        assert out.index("## Vendor-Specific") < out.index("RULE A BODY")

    def test_baked_rule_count_matches_process_files(self, tmp_path: Path) -> None:
        dotfiles = self._dotfiles(tmp_path, {"a.mdc": "x", "b.mdc": "y", "notes.txt": "z"})
        assert baked_rule_count(dotfiles) == 2
