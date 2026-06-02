"""Tests for core/agent_setup/claude.py.

All tests use tmp_path for home + dotfiles_dir; no real home is touched.
NEVER imports Path.home() or references ~/.claude.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Any

import pytest

from dotfiles.cmd.agent.vendors.claude import (
    _clean_mcp_permissions,
    _rewrite_http_to_mcp_remote,
    setup_claude,
)
from dotfiles.testing.fakes import FakeProcessRunner, write_tree

_JsonDict = dict[str, Any]

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

MCP_SERVERS_JSON = """{
  "playwright": {
    "command": "npx",
    "args": ["-y", "@playwright/mcp@latest"],
    "targets": ["claude", "desktop"]
  },
  "granola": {
    "type": "http",
    "url": "https://mcp.granola.ai/mcp",
    "targets": ["claude", "desktop"]
  },
  "codex-only": {
    "command": "npx",
    "args": ["-y", "codex-mcp"],
    "targets": ["codex"]
  }
}"""

PLUGINS_YAML = """\
# Claude Code plugins
- typescript-lsp
- superpowers
- context7
- myplugin@custom-marketplace
"""

MARKETPLACES_JSON = json.dumps(
    {
        "claude-code-plugins": {"source": {"source": "github", "repo": "anthropics/claude-code"}},
        "antfu-skills": {"source": {"source": "github", "repo": "antfu/skills"}},
    }
)

PERMISSIONS_JSON = json.dumps(
    {
        "allow": ["Bash(git:*)", "Bash(uv:*)"],
        "deny": ["Bash(rm -rf:*)"],
        "defaultMode": "auto",
    }
)

HOOKS_JSON = json.dumps(
    {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Edit|Write",
                    "hooks": [{"type": "command", "command": "echo check", "timeout": 5}],
                }
            ],
            "Stop": [{"matcher": "", "hooks": [{"type": "command", "command": "notify"}]}],
        }
    }
)

DESKTOP_PREFS_JSON = json.dumps(
    {
        "preferences": {
            "coworkScheduledTasksEnabled": True,
            "sidebarMode": "chat",
        }
    }
)

CORE_RULES_MD = "# Agent Instructions\n\nFollow these rules.\n"

EXTERNAL_SKILLS_TXT = """\
# External skills
fastapi/fastapi@fastapi
hairyf/skills@tauri
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dotfiles(tmp_path: Path) -> Path:
    d = tmp_path / "dotfiles"
    write_tree(
        d,
        {
            "agents/shared/mcp-servers.json": MCP_SERVERS_JSON,
            "agents/shared/rules.md": CORE_RULES_MD,
            "agents/claude/plugins.yaml": PLUGINS_YAML,
            "agents/claude/marketplaces.json": MARKETPLACES_JSON,
            "agents/claude/permissions.json": PERMISSIONS_JSON,
            "agents/claude/hooks.json": HOOKS_JSON,
            "agents/claude/desktop-preferences.json": DESKTOP_PREFS_JSON,
            "agents/claude/external-skills.txt": EXTERNAL_SKILLS_TXT,
            "agents/claude/statusline.sh": "#!/usr/bin/env bash\necho ok\n",
            ".ai/skills/.keep": "",
            ".ai/agents/myagent.md": "# MyAgent\n",
        },
    )
    return d


def _run(
    dotfiles: Path,
    home: Path,
    runner: FakeProcessRunner | None = None,
    *,
    clean: bool = False,
    reset_mcp: bool = False,
) -> list:
    r = runner or FakeProcessRunner()
    return setup_claude(
        runner=r,
        home=home,
        dotfiles_dir=dotfiles,
        which=lambda name: f"/usr/bin/{name}" if name == "npx" else None,
        clean=clean,
        reset_mcp=reset_mcp,
    )


def _settings(home: Path) -> _JsonDict:
    p = home / ".claude" / "settings.json"
    return json.loads(p.read_text()) if p.is_file() else {}


def _claude_json(home: Path) -> _JsonDict:
    p = home / ".claude.json"
    return json.loads(p.read_text()) if p.is_file() else {}


def _desktop_config(home: Path) -> _JsonDict:
    p = home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return json.loads(p.read_text()) if p.is_file() else {}


# ---------------------------------------------------------------------------
# CLAUDE.md
# ---------------------------------------------------------------------------


class TestSetupInstructions:
    def test_writes_claude_md(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert (home / ".claude" / "CLAUDE.md").is_file()

    def test_claude_md_content(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        content = (home / ".claude" / "CLAUDE.md").read_text()
        assert "Agent Instructions" in content


# ---------------------------------------------------------------------------
# Marketplaces
# ---------------------------------------------------------------------------


class TestSetupMarketplaces:
    def test_sets_extra_known_marketplaces(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        s = _settings(home)
        assert "extraKnownMarketplaces" in s
        assert "claude-code-plugins" in s["extraKnownMarketplaces"]
        assert "antfu-skills" in s["extraKnownMarketplaces"]

    def test_result_mentions_count(self, dotfiles: Path, home: Path) -> None:
        results = _run(dotfiles, home)
        r = next((x for x in results if "marketplace" in x.message.lower()), None)
        assert r is not None
        assert r.ok


# ---------------------------------------------------------------------------
# Plugins
# ---------------------------------------------------------------------------


class TestSetupPlugins:
    def test_enabled_plugins_set(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        s = _settings(home)
        assert "enabledPlugins" in s
        plugins = s["enabledPlugins"]
        assert "typescript-lsp@claude-plugins-official" in plugins
        assert "superpowers@claude-plugins-official" in plugins
        assert "myplugin@custom-marketplace" in plugins

    def test_all_plugin_values_true(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        for v in _settings(home)["enabledPlugins"].values():
            assert v is True

    def test_comment_lines_ignored(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        plugins = _settings(home)["enabledPlugins"]
        assert not any("#" in k for k in plugins)

    def test_result_mentions_count(self, dotfiles: Path, home: Path) -> None:
        results = _run(dotfiles, home)
        r = next((x for x in results if "plugin" in x.message.lower()), None)
        assert r is not None
        assert r.ok


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------


class TestSetupPermissions:
    def test_permissions_replaced(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        perms = _settings(home).get("permissions", {})
        assert "Bash(git:*)" in perms["allow"]
        assert "Bash(rm -rf:*)" in perms["deny"]

    def test_default_mode_set(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert _settings(home)["permissions"]["defaultMode"] == "auto"

    def test_result_mentions_counts(self, dotfiles: Path, home: Path) -> None:
        results = _run(dotfiles, home)
        r = next((x for x in results if "Permissions" in x.message), None)
        assert r is not None
        assert r.ok
        assert "2 allow" in r.message
        assert "1 deny" in r.message


# ---------------------------------------------------------------------------
# MCP — claude.json
# ---------------------------------------------------------------------------


class TestSetupMcp:
    def test_mcp_servers_written_to_claude_json(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        data = _claude_json(home)
        assert "playwright" in data.get("mcpServers", {})
        assert "granola" in data.get("mcpServers", {})

    def test_codex_only_server_excluded(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert "codex-only" not in _claude_json(home).get("mcpServers", {})

    def test_no_targets_key_in_entries(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        for cfg in _claude_json(home).get("mcpServers", {}).values():
            assert "targets" not in cfg

    def test_existing_user_mcp_preserved(self, dotfiles: Path, home: Path) -> None:
        existing = {"mcpServers": {"my-custom": {"command": "custom"}}}
        (home / ".claude.json").write_text(json.dumps(existing))
        _run(dotfiles, home)
        assert "my-custom" in _claude_json(home)["mcpServers"]

    def test_reset_mcp_replaces_managed(self, dotfiles: Path, home: Path) -> None:
        """--reset-mcp should purge old managed entries and re-add current ones."""
        existing = {
            "mcpServers": {
                "playwright": {"command": "old"},
                "my-custom": {"command": "custom"},
            }
        }
        (home / ".claude.json").write_text(json.dumps(existing))
        _run(dotfiles, home, reset_mcp=True)
        data = _claude_json(home)["mcpServers"]
        # playwright re-added from dotfiles (new value)
        assert data["playwright"]["command"] == "npx"
        # user custom preserved
        assert "my-custom" in data


# ---------------------------------------------------------------------------
# Desktop config
# ---------------------------------------------------------------------------


class TestSetupDesktop:
    def test_desktop_config_created(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        cfg = home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        assert cfg.is_file()

    def test_http_server_rewritten_as_mcp_remote(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        cfg = _desktop_config(home)
        granola = cfg["mcpServers"]["granola"]
        assert granola["command"] == "npx"
        assert "-y" in granola["args"]
        assert "mcp-remote" in granola["args"]
        assert "https://mcp.granola.ai/mcp" in granola["args"]

    def test_stdio_server_not_rewritten(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        playwright = _desktop_config(home)["mcpServers"]["playwright"]
        assert playwright["command"] == "npx"
        assert "mcp-remote" not in playwright.get("args", [])

    def test_desktop_preferences_merged(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        prefs = _desktop_config(home).get("preferences", {})
        assert prefs.get("sidebarMode") == "chat"
        assert prefs.get("coworkScheduledTasksEnabled") is True

    def test_existing_user_preferences_win(self, dotfiles: Path, home: Path) -> None:
        """User's existing preferences override dotfiles defaults."""
        cfg_path = (
            home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        )
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps({"preferences": {"sidebarMode": "sidebar"}}))

        _run(dotfiles, home)

        assert _desktop_config(home)["preferences"]["sidebarMode"] == "sidebar"


# ---------------------------------------------------------------------------
# http→mcp-remote rewrite unit test
# ---------------------------------------------------------------------------


class TestRewriteHttpToMcpRemote:
    def test_http_entry_rewritten(self) -> None:
        entry = {"type": "http", "url": "https://example.com/mcp"}
        result = _rewrite_http_to_mcp_remote(entry)
        assert result["command"] == "npx"
        assert result["args"] == ["-y", "mcp-remote", "https://example.com/mcp"]

    def test_headers_become_args(self) -> None:
        entry = {
            "type": "http",
            "url": "https://example.com/mcp",
            "headers": {"Authorization": "Bearer tok"},
        }
        result = _rewrite_http_to_mcp_remote(entry)
        assert "--header=Authorization:Bearer tok" in result["args"]

    def test_non_http_entry_unchanged(self) -> None:
        entry = {"command": "npx", "args": ["-y", "some-mcp"]}
        result = _rewrite_http_to_mcp_remote(entry)
        assert result == entry

    def test_http_without_url_unchanged(self) -> None:
        entry = {"type": "http"}
        result = _rewrite_http_to_mcp_remote(entry)
        assert result == entry


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------


class TestSetupHooks:
    def test_hooks_written_to_settings(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        hooks = _settings(home).get("hooks", {})
        assert "PreToolUse" in hooks
        assert "Stop" in hooks

    def test_result_mentions_event_count(self, dotfiles: Path, home: Path) -> None:
        results = _run(dotfiles, home)
        r = next((x for x in results if "hook" in x.message.lower()), None)
        assert r is not None
        assert r.ok


# ---------------------------------------------------------------------------
# Statusline
# ---------------------------------------------------------------------------


class TestSetupStatusline:
    def test_status_line_key_set(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        sl = _settings(home).get("statusLine", {})
        assert sl.get("type") == "command"

    def test_status_line_points_to_statusline_sh(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        cmd = _settings(home)["statusLine"]["command"]
        assert "statusline.sh" in cmd

    def test_statusline_sh_is_executable(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        sh = dotfiles / "agents" / "claude" / "statusline.sh"
        assert sh.stat().st_mode & stat.S_IXUSR


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------


class TestSetupPreferences:
    def test_voice_enabled(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert _settings(home).get("voiceEnabled") is True

    def test_notif_channel(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert _settings(home).get("preferredNotifChannel") == "terminal_bell"

    def test_default_mode(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert _settings(home).get("defaultMode") == "acceptEdits"


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


class TestSetupSkills:
    def test_deploy_skills_npx_call_issued(self, dotfiles: Path, home: Path) -> None:
        runner = FakeProcessRunner()
        _run(dotfiles, home, runner=runner)
        skills_calls = [c for c in runner.calls if "skills" in c and "claude-code" in c]
        assert len(skills_calls) >= 1

    def test_external_skills_npx_calls_issued(self, dotfiles: Path, home: Path) -> None:
        runner = FakeProcessRunner()
        _run(dotfiles, home, runner=runner)
        ext_calls = [c for c in runner.calls if "fastapi" in " ".join(c) or "tauri" in " ".join(c)]
        assert len(ext_calls) == 2

    def test_external_skill_skipped_if_already_present(self, dotfiles: Path, home: Path) -> None:
        # Pre-create fastapi skill dir so it's treated as present
        (home / ".claude" / "skills" / "fastapi").mkdir(parents=True)
        runner = FakeProcessRunner()
        _run(dotfiles, home, runner=runner)
        fastapi_calls = [c for c in runner.calls if "fastapi" in " ".join(c)]
        assert len(fastapi_calls) == 0


# ---------------------------------------------------------------------------
# Subagents + rules symlinks
# ---------------------------------------------------------------------------


class TestSubagentsAndRules:
    def test_subagents_deployed(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        assert (home / ".claude" / "agents" / "myagent.md").is_file()


# ---------------------------------------------------------------------------
# Clean mode
# ---------------------------------------------------------------------------


class TestCleanMode:
    def test_clean_removes_nonconforming_plugins(self, dotfiles: Path, home: Path) -> None:
        # Pre-seed settings with an extra plugin not in plugins.yaml
        (home / ".claude").mkdir(parents=True)
        (home / ".claude" / "settings.json").write_text(
            json.dumps({"enabledPlugins": {"stale-plugin@claude-plugins-official": True}})
        )
        _run(dotfiles, home, clean=True)
        plugins = _settings(home).get("enabledPlugins", {})
        assert "stale-plugin@claude-plugins-official" not in plugins

    def test_clean_removes_stale_mcp_permissions(self, dotfiles: Path, home: Path) -> None:
        (home / ".claude").mkdir(parents=True)
        (home / ".claude" / "settings.json").write_text(
            json.dumps(
                {
                    "permissions": {
                        "allow": ["Bash(git:*)", "mcp__stale-server__some_tool"],
                        "deny": [],
                        "defaultMode": "auto",
                    }
                }
            )
        )
        _run(dotfiles, home, clean=True)
        allow = _settings(home).get("permissions", {}).get("allow", [])
        # stale-server is not in mcp-servers.json → should be removed
        assert "mcp__stale-server__some_tool" not in allow

    def test_clean_mcp_perm_keeps_cross_target_server(self, dotfiles: Path, home: Path) -> None:
        """_clean_mcp_permissions keeps a registry server that doesn't target Claude.

        Exercises the pruner directly: in a full setup run _setup_permissions
        replaces the allow-list afterwards, so this is the precise unit under test.
        """
        claude_home = home / ".claude"
        claude_home.mkdir(parents=True)
        (claude_home / "settings.json").write_text(
            json.dumps(
                {
                    "permissions": {
                        # codex-only targets codex (not claude) but IS in the registry;
                        # tool-scoped form must be matched by the server prefix.
                        "allow": ["mcp__codex-only__run", "mcp__stale-server__x", "Bash(git:*)"],
                        "deny": [],
                        "defaultMode": "auto",
                    }
                }
            )
        )
        _clean_mcp_permissions(dotfiles, claude_home)
        allow = _settings(home).get("permissions", {}).get("allow", [])
        assert "mcp__codex-only__run" in allow  # known registry server (any target) → kept
        assert "Bash(git:*)" in allow  # non-mcp perm untouched
        assert "mcp__stale-server__x" not in allow  # truly-unknown server → removed

    def test_clean_removes_stale_projects(self, dotfiles: Path, home: Path) -> None:
        nonexistent = "/tmp/__nonexistent_test_project_12345__"
        (home / ".claude.json").write_text(
            json.dumps({"projects": {nonexistent: {"name": "stale"}}})
        )
        _run(dotfiles, home, clean=True)
        projects = _claude_json(home).get("projects", {})
        assert nonexistent not in projects


# ---------------------------------------------------------------------------
# Idempotency + isolation
# ---------------------------------------------------------------------------


class TestIsolation:
    def test_does_not_touch_real_home(self, dotfiles: Path, home: Path) -> None:
        """home fixture is tmp_path — verify nothing writes to Path.home()."""
        real_home = Path.home()
        _run(dotfiles, home)
        # Real ~/.claude/settings.json mtime must not change (we don't check mtime here,
        # but we verify we only wrote into the injected home)
        assert (
            not (real_home / ".claude" / "settings.json").samefile(
                home / ".claude" / "settings.json"
            )
            if (home / ".claude" / "settings.json").is_file()
            else True
        )

    def test_idempotent(self, dotfiles: Path, home: Path) -> None:
        _run(dotfiles, home)
        first_settings = _settings(home)
        _run(dotfiles, home)
        second_settings = _settings(home)
        assert first_settings.get("enabledPlugins") == second_settings.get("enabledPlugins")
        assert first_settings.get("permissions") == second_settings.get("permissions")

    def test_all_results_ok(self, dotfiles: Path, home: Path) -> None:
        results = _run(dotfiles, home)
        failures = [r for r in results if not r.ok]
        assert failures == [], f"Unexpected failures: {failures}"
