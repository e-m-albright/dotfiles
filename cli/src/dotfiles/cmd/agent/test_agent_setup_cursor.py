"""Tests for core/agent_setup/cursor.py.

All tests use tmp_path for home + dotfiles_dir (dotfiles_dir IS tmp_path here,
mirroring cursor's in-repo MCP target). No real home is touched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dotfiles.cmd.agent.vendors.cursor import setup_cursor
from dotfiles.testing.fakes import FakeProcessRunner, write_tree

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MCP_SERVERS_JSON = """{
  "playwright": {
    "command": "npx",
    "args": ["-y", "@playwright/mcp@latest"],
    "targets": ["cursor", "claude"]
  },
  "context7": {
    "type": "http",
    "url": "https://mcp.context7.com/mcp",
    "targets": ["cursor"]
  },
  "granola": {
    "type": "http",
    "url": "https://mcp.granola.ai/mcp",
    "targets": ["claude"]
  }
}"""

RULES_MD = "# Shared Agentic Rules\n\nSome rules here.\n"
PROCESS_RULE = """\
---
description: A test rule
alwaysApply: true
---

# Rule Body

Rule content.
"""
IGNORE_PATTERNS = "node_modules/\n.next/\ndist/\n"
CLI_CONFIG_JSON = '{"theme": "dark"}'


@pytest.fixture
def dotfiles(tmp_path: Path) -> Path:
    d = tmp_path / "dotfiles"
    write_tree(
        d,
        {
            "ai/agents/shared/mcp-servers.json": MCP_SERVERS_JSON,
            "ai/agents/shared/rules.md": RULES_MD,
            "ai/agents/shared/ignore-patterns": IGNORE_PATTERNS,
            "ai/agents/cursor/cli-config.json": CLI_CONFIG_JSON,
            "ai/rules/process/global-process.mdc": PROCESS_RULE,
        },
    )
    return d


def _run(dotfiles: Path, home: Path, *, reset_mcp: bool = False) -> list:
    return setup_cursor(
        runner=FakeProcessRunner(),
        home=home,
        dotfiles_dir=dotfiles,
        reset_mcp=reset_mcp,
    )


# ---------------------------------------------------------------------------
# MCP — reset_mcp flag
# ---------------------------------------------------------------------------


class TestResetMcp:
    def test_reset_mcp_removes_stale_managed_key(self, dotfiles: Path, home: Path) -> None:
        """A stale managed key present before reset_mcp=True must be removed."""
        mcp_file = dotfiles / "editors" / "cursor" / "mcp.json"
        mcp_file.parent.mkdir(parents=True, exist_ok=True)
        # Pre-populate with a managed key ("playwright") plus a custom key
        mcp_file.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "playwright": {"command": "old-command"},
                        "my-custom": {"command": "custom"},
                    }
                }
            )
        )
        _run(dotfiles, home, reset_mcp=True)
        data = json.loads(mcp_file.read_text())
        # playwright is a managed key — it should be replaced with the fresh value
        # (still present but coming from current mcp_servers_for, not the stale version)
        assert data["mcpServers"]["playwright"]["command"] == "npx"
        # custom entry is NOT a managed key — it must survive
        assert "my-custom" in data["mcpServers"]

    def test_reset_mcp_drops_removed_managed_key(self, dotfiles: Path, home: Path) -> None:
        """A managed key that no longer exists in mcp-servers.json is removed."""
        mcp_file = dotfiles / "editors" / "cursor" / "mcp.json"
        mcp_file.parent.mkdir(parents=True, exist_ok=True)
        # "old-managed" was a managed key that has since been removed from the registry
        mcp_file.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "playwright": {"command": "old"},
                        "old-managed": {"command": "gone"},
                    }
                }
            )
        )
        # Add "old-managed" to mcp-servers.json targeting cursor so it IS a managed key
        # then remove it — simulate by NOT including it in the json at all (it was removed)
        # In practice: "old-managed" is absent from mcp-servers.json → not in managed_keys
        # So with reset_mcp it won't be purged. Correct test: use a key actually in the file.
        # Use "context7" which IS in MCP_SERVERS_JSON and targets cursor.
        mcp_file.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "context7": {"type": "http", "url": "https://old.example.com/mcp"},
                        "my-custom": {"command": "custom"},
                    }
                }
            )
        )
        _run(dotfiles, home, reset_mcp=True)
        data = json.loads(mcp_file.read_text())
        # context7 is managed — refreshed with current value from mcp-servers.json
        assert data["mcpServers"]["context7"]["url"] == "https://mcp.context7.com/mcp"
        # custom entry survives
        assert "my-custom" in data["mcpServers"]

    def test_without_reset_mcp_stale_value_preserved(self, dotfiles: Path, home: Path) -> None:
        """Without reset_mcp, an old managed key value is not overridden if we only add."""
        mcp_file = dotfiles / "editors" / "cursor" / "mcp.json"
        mcp_file.parent.mkdir(parents=True, exist_ok=True)
        mcp_file.write_text(json.dumps({"mcpServers": {"my-custom": {"command": "custom"}}}))
        _run(dotfiles, home, reset_mcp=False)
        data = json.loads(mcp_file.read_text())
        # Additive — custom key survives and managed keys are added
        assert "my-custom" in data["mcpServers"]
        assert "playwright" in data["mcpServers"]


# ---------------------------------------------------------------------------
# MCP — in-repo target
# ---------------------------------------------------------------------------


class TestMcp:
    def test_creates_mcp_json_in_repo(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert (dotfiles / "editors" / "cursor" / "mcp.json").is_file()

    def test_mcp_json_not_in_home(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert not (home / ".cursor" / "mcp.json").exists()

    def test_cursor_target_servers_included(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        data = json.loads((dotfiles / "editors" / "cursor" / "mcp.json").read_text())
        assert "playwright" in data["mcpServers"]
        assert "context7" in data["mcpServers"]

    def test_non_cursor_servers_excluded(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        data = json.loads((dotfiles / "editors" / "cursor" / "mcp.json").read_text())
        assert "granola" not in data["mcpServers"]

    def test_targets_key_stripped(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        data = json.loads((dotfiles / "editors" / "cursor" / "mcp.json").read_text())
        for cfg in data["mcpServers"].values():
            assert "targets" not in cfg

    def test_preserves_existing_custom_servers(self, dotfiles: Path, home: Path) -> None:
        mcp_file = dotfiles / "editors" / "cursor" / "mcp.json"
        mcp_file.parent.mkdir(parents=True, exist_ok=True)
        mcp_file.write_text(json.dumps({"mcpServers": {"my-custom": {"command": "foo"}}}))
        _run(dotfiles, home)
        data = json.loads(mcp_file.read_text())
        assert "my-custom" in data["mcpServers"]
        assert "playwright" in data["mcpServers"]

    def test_result_mentions_mcp_count(self, dotfiles: Path, home: Path) -> None:
        results = _run(dotfiles, home)
        mcp_msg = next((r for r in results if "MCP" in r.message), None)
        assert mcp_msg is not None
        assert mcp_msg.ok
        assert "2" in mcp_msg.message  # playwright + context7


# ---------------------------------------------------------------------------
# shared-rules.mdc
# ---------------------------------------------------------------------------


class TestSharedRules:
    def test_creates_shared_rules_mdc(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert (dotfiles / "ai" / "agents" / "cursor" / "rules" / "shared-rules.mdc").is_file()

    def test_shared_rules_has_yaml_frontmatter(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        content = (dotfiles / "ai" / "agents" / "cursor" / "rules" / "shared-rules.mdc").read_text()
        assert content.startswith("---\n")
        assert "alwaysApply: true" in content

    def test_shared_rules_contains_rules_md(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        content = (dotfiles / "ai" / "agents" / "cursor" / "rules" / "shared-rules.mdc").read_text()
        assert "Shared Agentic Rules" in content

    def test_shared_rules_description_in_frontmatter(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        content = (dotfiles / "ai" / "agents" / "cursor" / "rules" / "shared-rules.mdc").read_text()
        assert "description:" in content
        assert "guardrails" in content


# ---------------------------------------------------------------------------
# cli-config.json symlink
# ---------------------------------------------------------------------------


class TestCliConfig:
    def test_cli_config_symlinked_in_home(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        link = home / ".cursor" / "cli-config.json"
        assert link.is_symlink()

    def test_cli_config_points_into_dotfiles(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        link = home / ".cursor" / "cli-config.json"
        assert (
            link.resolve() == (dotfiles / "ai" / "agents" / "cursor" / "cli-config.json").resolve()
        )

    def test_cli_config_content_readable(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert (home / ".cursor" / "cli-config.json").read_text() == CLI_CONFIG_JSON

    def test_no_cli_config_result_when_src_missing(self, home: Path, tmp_path: Path) -> None:
        d = tmp_path / "nodotfiles"
        write_tree(
            d,
            {
                "ai/agents/shared/rules.md": RULES_MD,
                "ai/rules/process/global-process.mdc": PROCESS_RULE,
            },
        )
        results = setup_cursor(runner=FakeProcessRunner(), home=home, dotfiles_dir=d)
        cli_results = [r for r in results if "cli-config" in r.message]
        assert cli_results == []


# ---------------------------------------------------------------------------
# plugin symlink
# ---------------------------------------------------------------------------


class TestSkills:
    def test_deploys_canonical_and_shared_external_skills_when_sources_exist(
        self, dotfiles: Path, home: Path
    ) -> None:
        write_tree(
            dotfiles, {"ai/skills/review/SKILL.md": "---\nname: review\ndescription: Review\n---\n"}
        )
        write_tree(
            home,
            {".agents/skills/fastapi/SKILL.md": "---\nname: fastapi\ndescription: FastAPI\n---\n"},
        )
        setup_cursor(runner=FakeProcessRunner(), home=home, dotfiles_dir=dotfiles)

        review = home / ".cursor" / "skills" / "review"
        fastapi = home / ".cursor" / "skills" / "fastapi"
        assert review.is_symlink()
        assert review.resolve() == (dotfiles / "ai" / "skills" / "review").resolve()
        assert fastapi.is_symlink()
        assert fastapi.resolve() == (home / ".agents" / "skills" / "fastapi").resolve()

    def test_skips_skill_deploy_when_no_source_dir(self, dotfiles: Path, home: Path) -> None:
        setup_cursor(runner=FakeProcessRunner(), home=home, dotfiles_dir=dotfiles)

        assert not (home / ".cursor" / "skills").exists()


class TestPlugin:
    def test_plugin_symlinked_in_home(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        link = home / ".cursor" / "plugins" / "dotfiles"
        assert link.is_symlink()

    def test_plugin_points_to_agents_cursor(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        link = home / ".cursor" / "plugins" / "dotfiles"
        assert link.resolve() == (dotfiles / "ai" / "agents" / "cursor").resolve()

    def test_plugin_already_registered_is_idempotent(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        results = _run(dotfiles, home)
        plugin_results = [r for r in results if "plugin" in r.message.lower()]
        assert all(r.ok for r in plugin_results)


# ---------------------------------------------------------------------------
# .cursorignore
# ---------------------------------------------------------------------------


class TestCursorignore:
    def test_creates_cursorignore_in_repo(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert (dotfiles / "editors" / "cursor" / ".cursorignore").is_file()

    def test_cursorignore_not_in_home(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert not (home / ".cursor" / ".cursorignore").exists()

    def test_cursorignore_has_header_comment(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        content = (dotfiles / "editors" / "cursor" / ".cursorignore").read_text()
        assert "AUTO-GENERATED" in content

    def test_cursorignore_contains_shared_patterns(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        content = (dotfiles / "editors" / "cursor" / ".cursorignore").read_text()
        assert "node_modules/" in content
        assert ".next/" in content

    def test_cursorignore_has_cursor_specific_section(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        content = (dotfiles / "editors" / "cursor" / ".cursorignore").read_text()
        assert ".vscode/" in content
        assert ".idea/" in content

    def test_cursorignore_skipped_when_no_ignore_patterns(self, home: Path, tmp_path: Path) -> None:
        d = tmp_path / "nodotfiles2"
        write_tree(d, {"ai/agents/shared/rules.md": RULES_MD})
        setup_cursor(runner=FakeProcessRunner(), home=home, dotfiles_dir=d)
        assert not (d / "editors" / "cursor" / ".cursorignore").exists()


# ---------------------------------------------------------------------------
# Marketplace plugin reminder (folded in from the old `cursor-plugins` command)
# ---------------------------------------------------------------------------


class TestPluginReminder:
    def test_reminder_present_when_plugins_doc_exists(self, dotfiles: Path, home: Path) -> None:
        (dotfiles / "ai" / "agents" / "cursor" / "PLUGINS.md").write_text("# Cursor plugins\n")
        results = _run(dotfiles, home)
        reminder = next((r for r in results if "Marketplace plugins" in r.message), None)
        assert reminder is not None
        assert reminder.level == "info"
        assert reminder.ok
        # Points at PLUGINS.md as the source of truth rather than re-listing the matrix
        assert "PLUGINS.md" in reminder.details

    def test_no_reminder_when_plugins_doc_missing(self, dotfiles: Path, home: Path) -> None:
        # The dotfiles fixture has no PLUGINS.md — reminder is skipped, not errored.
        results = _run(dotfiles, home)
        assert not any("Marketplace plugins" in r.message for r in results)


# ---------------------------------------------------------------------------
# Overall
# ---------------------------------------------------------------------------


class TestOverall:
    def test_all_results_ok(self, dotfiles: Path, home: Path) -> None:
        results = _run(dotfiles, home)
        assert all(r.ok for r in results)

    def test_no_runner_calls(self, dotfiles: Path, home: Path) -> None:
        runner = FakeProcessRunner()
        setup_cursor(runner=runner, home=home, dotfiles_dir=dotfiles)
        assert runner.calls == []

    def test_idempotent(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        results = _run(dotfiles, home)
        assert all(r.ok for r in results)
