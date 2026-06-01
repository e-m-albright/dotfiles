"""Tests for core/agent_setup/codex.py.

All tests use tmp_path for home + dotfiles_dir; no real home is touched.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from dotfiles.core.agent_setup.codex import setup_codex
from tests.fakes import FakeProcessRunner, write_tree

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

MCP_SERVERS_JSON = """{
  "playwright": {
    "command": "npx",
    "args": ["-y", "@playwright/mcp@latest"],
    "targets": ["codex", "claude"]
  },
  "granola": {
    "type": "http",
    "url": "https://mcp.granola.ai/mcp",
    "targets": ["claude"]
  },
  "context7": {
    "command": "npx",
    "args": ["-y", "@upstash/context7-mcp"],
    "targets": ["codex"]
  }
}"""

RULES_MD = "# Shared Agentic Rules\n\nUniversal guardrails.\n"

PROCESS_RULE = """\
---
description: Global process rule
alwaysApply: true
---

# Rule Body

Rule content here.
"""

DEFAULT_RULES = """\
# default.rules
prefix_rule(pattern=["uv", "run"], decision="allow")
prefix_rule(pattern=["git", "add"], decision="allow")
prefix_rule(pattern=["git", "commit"], decision="allow")
"""

STATUSLINE_TOML = """\
theme = "Sublime Snazzy"
status_line = [
  "app-name",
  "git-branch",
]
"""

HOOKS_JSON = json.dumps(
    {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Edit|Write",
                    "hooks": [{"type": "command", "command": "echo check", "timeout": 5}],
                }
            ]
        }
    }
)


@pytest.fixture
def dotfiles(tmp_path: Path) -> Path:
    d = tmp_path / "dotfiles"
    write_tree(
        d,
        {
            "agents/shared/mcp-servers.json": MCP_SERVERS_JSON,
            "agents/shared/rules.md": RULES_MD,
            "agents/codex/default.rules": DEFAULT_RULES,
            "agents/codex/statusline.toml": STATUSLINE_TOML,
            "agents/codex/hooks.json": HOOKS_JSON,
            ".ai/rules/process/global-process.mdc": PROCESS_RULE,
            ".ai/skills/.keep": "",  # skills dir must exist for deploy_skills
            ".ai/agents/myagent.md": "# MyAgent\n",
        },
    )
    return d


@pytest.fixture
def home(tmp_path: Path) -> Path:
    h = tmp_path / "home"
    h.mkdir()
    return h


def _runner() -> FakeProcessRunner:
    r = FakeProcessRunner()
    # npx must exist for deploy_skills
    return r


def _run(dotfiles: Path, home: Path, runner: FakeProcessRunner | None = None) -> list:
    r = runner or _runner()
    return setup_codex(
        runner=r,
        home=home,
        dotfiles_dir=dotfiles,
        which=lambda name: f"/usr/bin/{name}" if name == "npx" else None,
    )


# ---------------------------------------------------------------------------
# AGENTS.md
# ---------------------------------------------------------------------------


class TestSetupInstructions:
    def test_creates_agents_md(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert (home / ".codex" / "AGENTS.md").is_file()

    def test_agents_md_starts_with_header(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        content = (home / ".codex" / "AGENTS.md").read_text()
        assert content.startswith("# Global Agent Instructions")

    def test_agents_md_contains_shared_rules(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        content = (home / ".codex" / "AGENTS.md").read_text()
        assert "Shared Agentic Rules" in content

    def test_agents_md_contains_codex_specific_section(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        content = (home / ".codex" / "AGENTS.md").read_text()
        assert "## Codex-Specific" in content
        assert "AGENTS.md as the primary instruction file" in content

    def test_agents_md_contains_baked_rules(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        content = (home / ".codex" / "AGENTS.md").read_text()
        assert "## global-process" in content

    def test_result_mentions_rule_count(self, dotfiles: Path, home: Path) -> None:
        results = _run(dotfiles, home)
        instructions_result = next((r for r in results if "baked rules" in r.message), None)
        assert instructions_result is not None
        assert "1" in instructions_result.message  # 1 .mdc file in fixture


# ---------------------------------------------------------------------------
# default.rules copy / guard
# ---------------------------------------------------------------------------


class TestSetupDefaultRules:
    def test_copies_default_rules(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        dest = home / ".codex" / "rules" / "default.rules"
        assert dest.is_file()
        assert dest.read_text() == DEFAULT_RULES

    def test_result_mentions_rule_count(self, dotfiles: Path, home: Path) -> None:
        results = _run(dotfiles, home)
        rules_result = next((r for r in results if "auto-approve rules" in r.message), None)
        assert rules_result is not None
        assert rules_result.ok

    def test_does_not_overwrite_when_live_file_is_larger(self, dotfiles: Path, home: Path) -> None:
        """Refuse to overwrite if live file has MORE lines than source."""
        rules_dir = home / ".codex" / "rules"
        rules_dir.mkdir(parents=True)
        bigger = DEFAULT_RULES + '\nprefix_rule(pattern=["custom"], decision="allow")\n'
        (rules_dir / "default.rules").write_text(bigger)

        _run(dotfiles, home)

        # File should still have the larger content (not replaced)
        live = (rules_dir / "default.rules").read_text()
        assert "custom" in live

    def test_does_not_overwrite_result_message(self, dotfiles: Path, home: Path) -> None:
        """Result message should say 'leaving in place' when guard fires."""
        rules_dir = home / ".codex" / "rules"
        rules_dir.mkdir(parents=True)
        bigger = DEFAULT_RULES + '\nprefix_rule(pattern=["extra"], decision="allow")\n'
        (rules_dir / "default.rules").write_text(bigger)

        results = _run(dotfiles, home)
        guard_result = next((r for r in results if "leaving in place" in r.message.lower()), None)
        assert guard_result is not None

    def test_overwrites_when_same_size(self, dotfiles: Path, home: Path) -> None:
        """If live file has same line count (but different content), overwrite."""
        rules_dir = home / ".codex" / "rules"
        rules_dir.mkdir(parents=True)
        # Same number of lines, different content
        same_lines = DEFAULT_RULES.replace("uv", "xx")
        (rules_dir / "default.rules").write_text(same_lines)

        _run(dotfiles, home)

        live = (rules_dir / "default.rules").read_text()
        assert 'pattern=["uv", "run"]' in live


# ---------------------------------------------------------------------------
# MCP (config.toml)
# ---------------------------------------------------------------------------


class TestSetupMcp:
    def test_creates_config_toml(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert (home / ".codex" / "config.toml").is_file()

    def test_config_toml_is_valid_toml(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        text = (home / ".codex" / "config.toml").read_text()
        parsed = tomllib.loads(text)
        assert "mcp_servers" in parsed

    def test_codex_target_server_included(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        parsed = tomllib.loads((home / ".codex" / "config.toml").read_text())
        assert "playwright" in parsed["mcp_servers"]
        assert "context7" in parsed["mcp_servers"]

    def test_claude_only_target_included_as_fallback(self, dotfiles: Path, home: Path) -> None:
        """granola targets only claude — but codex setup.sh includes claude targets too."""
        _run(dotfiles, home)
        parsed = tomllib.loads((home / ".codex" / "config.toml").read_text())
        assert "granola" in parsed["mcp_servers"]

    def test_no_targets_key_in_mcp_entries(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        parsed = tomllib.loads((home / ".codex" / "config.toml").read_text())
        for cfg in parsed["mcp_servers"].values():
            assert "targets" not in cfg

    def test_preserves_existing_non_mcp_section(self, dotfiles: Path, home: Path) -> None:
        """Pre-existing [other] section must survive the MCP upsert."""
        config_toml = home / ".codex"
        config_toml.mkdir(parents=True)
        existing = '[other]\nfoo = "bar"\n'
        (config_toml / "config.toml").write_text(existing)

        _run(dotfiles, home)

        parsed = tomllib.loads((config_toml / "config.toml").read_text())
        assert parsed.get("other", {}).get("foo") == "bar"
        assert "mcp_servers" in parsed

    def test_idempotent(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        first = (home / ".codex" / "config.toml").read_text()
        _run(dotfiles, home)
        second = (home / ".codex" / "config.toml").read_text()
        # MCP server count should be the same both times
        p1 = tomllib.loads(first)
        p2 = tomllib.loads(second)
        assert set(p1["mcp_servers"].keys()) == set(p2["mcp_servers"].keys())


# ---------------------------------------------------------------------------
# Statusline injection
# ---------------------------------------------------------------------------


class TestSetupStatusline:
    def test_statusline_injected_into_tui_section(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        parsed = tomllib.loads((home / ".codex" / "config.toml").read_text())
        assert "tui" in parsed
        assert parsed["tui"]["theme"] == "Sublime Snazzy"

    def test_creates_tui_section_if_absent(self, dotfiles: Path, home: Path) -> None:
        """When no [tui] in existing config, one should be appended."""
        codex_home = home / ".codex"
        codex_home.mkdir(parents=True)
        (codex_home / "config.toml").write_text("[other]\nval = 1\n")

        _run(dotfiles, home)

        parsed = tomllib.loads((codex_home / "config.toml").read_text())
        assert "tui" in parsed

    def test_existing_theme_key_replaced(self, dotfiles: Path, home: Path) -> None:
        """Pre-existing theme= under [tui] should be replaced by statusline.toml value."""
        codex_home = home / ".codex"
        codex_home.mkdir(parents=True)
        (codex_home / "config.toml").write_text('[tui]\ntheme = "OldTheme"\n')

        _run(dotfiles, home)

        parsed = tomllib.loads((codex_home / "config.toml").read_text())
        assert parsed["tui"]["theme"] == "Sublime Snazzy"


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------


class TestSetupHooks:
    def test_copies_hooks_json(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        dest = home / ".codex" / "hooks.json"
        assert dest.is_file()
        data = json.loads(dest.read_text())
        assert "hooks" in data

    def test_result_ok(self, dotfiles: Path, home: Path) -> None:
        results = _run(dotfiles, home)
        hooks_result = next((r for r in results if "hooks" in r.message.lower()), None)
        assert hooks_result is not None
        assert hooks_result.ok


# ---------------------------------------------------------------------------
# Skills + subagents
# ---------------------------------------------------------------------------


class TestSkillsAndSubagents:
    def test_deploy_skills_command_issued(self, dotfiles: Path, home: Path) -> None:
        runner = _runner()
        _run(dotfiles, home, runner=runner)
        npx_calls = [c for c in runner.calls if "npx" in c and "skills" in c]
        assert len(npx_calls) >= 1

    def test_deploy_skills_uses_codex_vendor(self, dotfiles: Path, home: Path) -> None:
        runner = _runner()
        _run(dotfiles, home, runner=runner)
        skills_call = next((c for c in runner.calls if "npx" in c and "skills" in c), None)
        assert skills_call is not None
        assert "codex" in skills_call

    def test_subagents_deployed(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert (home / ".codex" / "agents" / "myagent.md").is_file()


# ---------------------------------------------------------------------------
# All results OK
# ---------------------------------------------------------------------------


class TestAllResultsOk:
    def test_all_results_ok(self, dotfiles: Path, home: Path) -> None:
        results = _run(dotfiles, home)
        failures = [r for r in results if not r.ok]
        assert failures == [], f"Unexpected failures: {failures}"
