"""Tests for core/agent_setup/gemini.py.

All tests use tmp_path for home + dotfiles_dir; no real home is touched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dotfiles.core.agent_setup.gemini import setup_gemini
from tests.fakes import FakeProcessRunner, write_tree

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MCP_SERVERS_JSON = """{
  "playwright": {
    "command": "npx",
    "args": ["-y", "@playwright/mcp@latest"],
    "targets": ["gemini", "claude"]
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
GEMINI_SEED_SETTINGS = json.dumps(
    {
        "$comment": "Gemini settings",
        "security": {"auth": {"selectedType": "oauth-personal"}},
        "mcpServers": {},
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
            "agents/gemini/settings.json": GEMINI_SEED_SETTINGS,
            ".ai/rules/process/global-process.mdc": PROCESS_RULE,
        },
    )
    return d


@pytest.fixture
def home(tmp_path: Path) -> Path:
    h = tmp_path / "home"
    h.mkdir()
    return h


def _runner() -> FakeProcessRunner:
    return FakeProcessRunner()


# ---------------------------------------------------------------------------
# gemini absent → skipped
# ---------------------------------------------------------------------------


class TestGeminiAbsent:
    def test_returns_single_skipped_result(self, dotfiles: Path, home: Path) -> None:
        results = setup_gemini(
            runner=_runner(),
            home=home,
            dotfiles_dir=dotfiles,
            which=lambda _: None,
        )
        assert len(results) == 1
        assert results[0].ok
        assert "skipped" in results[0].message.lower()
        assert "gemini not installed" in results[0].message.lower()

    def test_no_files_written_when_skipped(self, dotfiles: Path, home: Path) -> None:
        setup_gemini(
            runner=_runner(),
            home=home,
            dotfiles_dir=dotfiles,
            which=lambda _: None,
        )
        assert not (home / ".gemini").exists()


# ---------------------------------------------------------------------------
# gemini present
# ---------------------------------------------------------------------------


class TestGeminiPresent:
    def _run(self, dotfiles: Path, home: Path) -> list:
        return setup_gemini(
            runner=_runner(),
            home=home,
            dotfiles_dir=dotfiles,
            which=lambda name: "/usr/bin/gemini" if name == "gemini" else None,
        )

    def test_creates_gemini_home_dir(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        assert (home / ".gemini").is_dir()

    def test_all_results_ok(self, dotfiles: Path, home: Path) -> None:
        results = self._run(dotfiles, home)
        assert all(r.ok for r in results)

    def test_seeds_settings_json_when_missing(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        settings_file = home / ".gemini" / "settings.json"
        assert settings_file.is_file()
        data = json.loads(settings_file.read_text())
        # Should contain the seed content
        assert "security" in data

    def test_does_not_overwrite_existing_settings(self, dotfiles: Path, home: Path) -> None:
        gemini_home = home / ".gemini"
        gemini_home.mkdir(parents=True)
        existing = {"my": "custom-settings", "mcpServers": {}}
        (gemini_home / "settings.json").write_text(json.dumps(existing))

        self._run(dotfiles, home)

        data = json.loads((gemini_home / "settings.json").read_text())
        assert data["my"] == "custom-settings"

    def test_merges_mcp_servers_into_settings(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        settings_file = home / ".gemini" / "settings.json"
        data = json.loads(settings_file.read_text())
        # playwright targets gemini; granola targets only claude → not included
        assert "playwright" in data["mcpServers"]
        assert "granola" not in data["mcpServers"]

    def test_mcp_entry_has_no_targets_key(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        settings_file = home / ".gemini" / "settings.json"
        data = json.loads(settings_file.read_text())
        for cfg in data["mcpServers"].values():
            assert "targets" not in cfg

    def test_writes_gemini_md(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        md = home / ".gemini" / "GEMINI.md"
        assert md.is_file()

    def test_gemini_md_starts_with_header(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        content = (home / ".gemini" / "GEMINI.md").read_text()
        assert content.startswith("# Global Agent Instructions")

    def test_gemini_md_contains_rules_md(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        content = (home / ".gemini" / "GEMINI.md").read_text()
        assert "Shared Agentic Rules" in content

    def test_gemini_md_contains_baked_rules(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        content = (home / ".gemini" / "GEMINI.md").read_text()
        # baked rules include the rule name as a heading
        assert "## global-process" in content

    def test_settings_result_mentions_mcp_count(self, dotfiles: Path, home: Path) -> None:
        results = self._run(dotfiles, home)
        mcp_msg = next((r for r in results if "MCP" in r.message), None)
        assert mcp_msg is not None
        assert "1" in mcp_msg.message  # 1 gemini-target server

    def test_idempotent(self, dotfiles: Path, home: Path) -> None:
        """Running twice should not raise and should produce the same output."""
        self._run(dotfiles, home)
        results = self._run(dotfiles, home)
        assert all(r.ok for r in results)

    def test_no_runner_calls_made(self, dotfiles: Path, home: Path) -> None:
        """Gemini setup doesn't invoke any subprocesses."""
        runner = _runner()
        setup_gemini(
            runner=runner,
            home=home,
            dotfiles_dir=dotfiles,
            which=lambda name: "/usr/bin/gemini" if name == "gemini" else None,
        )
        assert runner.calls == []

    def test_skips_mcp_when_no_mcp_servers_json(self, home: Path, tmp_path: Path) -> None:
        """Should not crash when mcp-servers.json is absent."""
        d = tmp_path / "dotfiles2"
        write_tree(
            d,
            {
                "agents/shared/rules.md": RULES_MD,
                "agents/gemini/settings.json": GEMINI_SEED_SETTINGS,
                ".ai/rules/process/global-process.mdc": PROCESS_RULE,
            },
        )
        results = setup_gemini(
            runner=_runner(),
            home=home,
            dotfiles_dir=d,
            which=lambda name: "/usr/bin/gemini" if name == "gemini" else None,
        )
        assert all(r.ok for r in results)
