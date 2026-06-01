"""Tests for core/agent_setup/cursor.py.

All tests use tmp_path for home + dotfiles_dir (dotfiles_dir IS tmp_path here,
mirroring cursor's in-repo MCP target). No real home is touched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dotfiles.core.agent_setup.cursor import setup_cursor
from tests.fakes import FakeProcessRunner, write_tree

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
            "agents/shared/mcp-servers.json": MCP_SERVERS_JSON,
            "agents/shared/rules.md": RULES_MD,
            "agents/shared/ignore-patterns": IGNORE_PATTERNS,
            "agents/cursor/cli-config.json": CLI_CONFIG_JSON,
            ".ai/rules/process/global-process.mdc": PROCESS_RULE,
        },
    )
    return d


@pytest.fixture
def home(tmp_path: Path) -> Path:
    h = tmp_path / "home"
    h.mkdir()
    return h


def _run(dotfiles: Path, home: Path) -> list:
    return setup_cursor(
        runner=FakeProcessRunner(),
        home=home,
        dotfiles_dir=dotfiles,
    )


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
        assert (dotfiles / "agents" / "cursor" / "rules" / "shared-rules.mdc").is_file()

    def test_shared_rules_has_yaml_frontmatter(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        content = (dotfiles / "agents" / "cursor" / "rules" / "shared-rules.mdc").read_text()
        assert content.startswith("---\n")
        assert "alwaysApply: true" in content

    def test_shared_rules_contains_rules_md(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        content = (dotfiles / "agents" / "cursor" / "rules" / "shared-rules.mdc").read_text()
        assert "Shared Agentic Rules" in content

    def test_shared_rules_description_in_frontmatter(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        content = (dotfiles / "agents" / "cursor" / "rules" / "shared-rules.mdc").read_text()
        assert "description:" in content
        assert "guardrails" in content


# ---------------------------------------------------------------------------
# process rules symlinks (.mdc suffix)
# ---------------------------------------------------------------------------


class TestProcessRules:
    def test_process_rules_symlinked_with_mdc_suffix(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        link = dotfiles / "agents" / "cursor" / "rules" / "global-process.mdc"
        assert link.is_symlink()

    def test_process_rule_symlink_points_to_source(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        link = dotfiles / "agents" / "cursor" / "rules" / "global-process.mdc"
        assert (
            link.resolve()
            == (dotfiles / ".ai" / "rules" / "process" / "global-process.mdc").resolve()
        )


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
        assert link.resolve() == (dotfiles / "agents" / "cursor" / "cli-config.json").resolve()

    def test_cli_config_content_readable(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert (home / ".cursor" / "cli-config.json").read_text() == CLI_CONFIG_JSON

    def test_no_cli_config_result_when_src_missing(self, home: Path, tmp_path: Path) -> None:
        d = tmp_path / "nodotfiles"
        write_tree(
            d,
            {
                "agents/shared/rules.md": RULES_MD,
                ".ai/rules/process/global-process.mdc": PROCESS_RULE,
            },
        )
        results = setup_cursor(runner=FakeProcessRunner(), home=home, dotfiles_dir=d)
        cli_results = [r for r in results if "cli-config" in r.message]
        assert cli_results == []


# ---------------------------------------------------------------------------
# plugin symlink
# ---------------------------------------------------------------------------


class TestPlugin:
    def test_plugin_symlinked_in_home(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        link = home / ".cursor" / "plugins" / "dotfiles"
        assert link.is_symlink()

    def test_plugin_points_to_agents_cursor(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        link = home / ".cursor" / "plugins" / "dotfiles"
        assert link.resolve() == (dotfiles / "agents" / "cursor").resolve()

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
        write_tree(d, {"agents/shared/rules.md": RULES_MD})
        setup_cursor(runner=FakeProcessRunner(), home=home, dotfiles_dir=d)
        assert not (d / "editors" / "cursor" / ".cursorignore").exists()


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
