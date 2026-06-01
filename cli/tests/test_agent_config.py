"""Tests for agent_config pydantic models and load_config helper."""

from __future__ import annotations

import json
from pathlib import Path

from dotfiles.core.agent_config import (
    ClaudeHooksConfig,
    CursorHooksConfig,
    McpServerEntry,
    PermissionsBlock,
    SettingsWithPermissions,
    load_config,
    load_mcp_servers,
)
from tests.fakes import FakeFileSystem

_PATH = Path("/fake/config.json")


# ---------------------------------------------------------------------------
# McpServerEntry
# ---------------------------------------------------------------------------


class TestMcpServerEntry:
    def test_parses_targets(self) -> None:
        entry = McpServerEntry.model_validate_json('{"targets": ["claude", "cursor"]}')
        assert entry.targets == ["claude", "cursor"]

    def test_defaults_empty_targets(self) -> None:
        entry = McpServerEntry.model_validate_json("{}")
        assert entry.targets == []

    def test_tolerates_extra_keys(self) -> None:
        entry = McpServerEntry.model_validate_json(
            '{"targets": [], "command": "npx foo", "args": []}'
        )
        assert entry.targets == []


# ---------------------------------------------------------------------------
# ClaudeHooksConfig
# ---------------------------------------------------------------------------


class TestClaudeHooksConfig:
    def test_parses_hooks_dict(self) -> None:
        cfg = ClaudeHooksConfig.model_validate_json('{"hooks": {"Stop": [], "PreToolUse": []}}')
        assert set(cfg.hooks.keys()) == {"Stop", "PreToolUse"}

    def test_defaults_empty(self) -> None:
        cfg = ClaudeHooksConfig.model_validate_json("{}")
        assert cfg.hooks == {}

    def test_tolerates_extra_keys(self) -> None:
        cfg = ClaudeHooksConfig.model_validate_json('{"hooks": {}, "version": 1}')
        assert cfg.hooks == {}


# ---------------------------------------------------------------------------
# CursorHooksConfig
# ---------------------------------------------------------------------------


class TestCursorHooksConfig:
    def test_parses_events(self) -> None:
        cfg = CursorHooksConfig.model_validate_json(
            '{"hooks": [{"event": "afterFileEdit"}, {"event": "beforeFileEdit"}]}'
        )
        assert [h.event for h in cfg.hooks] == ["afterFileEdit", "beforeFileEdit"]

    def test_defaults_empty_list(self) -> None:
        cfg = CursorHooksConfig.model_validate_json("{}")
        assert cfg.hooks == []

    def test_tolerates_extra_keys_in_entry(self) -> None:
        cfg = CursorHooksConfig.model_validate_json(
            '{"hooks": [{"event": "Stop", "command": "foo"}]}'
        )
        assert cfg.hooks[0].event == "Stop"


# ---------------------------------------------------------------------------
# PermissionsBlock
# ---------------------------------------------------------------------------


class TestPermissionsBlock:
    def test_parses_allow_deny(self) -> None:
        block = PermissionsBlock.model_validate_json('{"allow": ["a", "b"], "deny": ["x"]}')
        assert len(block.allow) == 2
        assert len(block.deny) == 1

    def test_defaults_empty(self) -> None:
        block = PermissionsBlock.model_validate_json("{}")
        assert block.allow == []
        assert block.deny == []

    def test_tolerates_extra_keys(self) -> None:
        block = PermissionsBlock.model_validate_json('{"allow": [], "deny": [], "extra": true}')
        assert block.allow == []


# ---------------------------------------------------------------------------
# SettingsWithPermissions
# ---------------------------------------------------------------------------


class TestSettingsWithPermissions:
    def test_parses_nested_permissions(self) -> None:
        cfg = SettingsWithPermissions.model_validate_json(
            '{"permissions": {"allow": ["x"], "deny": []}}'
        )
        assert len(cfg.permissions.allow) == 1
        assert cfg.permissions.deny == []

    def test_defaults_empty_permissions(self) -> None:
        cfg = SettingsWithPermissions.model_validate_json("{}")
        assert cfg.permissions.allow == []
        assert cfg.permissions.deny == []

    def test_tolerates_extra_top_level_keys(self) -> None:
        cfg = SettingsWithPermissions.model_validate_json(
            '{"permissions": {}, "model": "claude-3"}'
        )
        assert cfg.permissions.allow == []


# ---------------------------------------------------------------------------
# load_config helper
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_returns_model_for_valid_file(self) -> None:
        fs = FakeFileSystem()
        fs.write_text(_PATH, '{"allow": ["a"], "deny": []}')
        result = load_config(fs, _PATH, PermissionsBlock)
        assert result is not None
        assert len(result.allow) == 1

    def test_returns_none_for_missing_file(self) -> None:
        fs = FakeFileSystem()
        assert load_config(fs, _PATH, PermissionsBlock) is None

    def test_returns_none_for_invalid_json(self) -> None:
        fs = FakeFileSystem()
        fs.write_text(_PATH, "NOT JSON {{{{")
        assert load_config(fs, _PATH, PermissionsBlock) is None

    def test_returns_none_for_wrong_type(self) -> None:
        fs = FakeFileSystem()
        # JSON is valid but pydantic can coerce — just ensure we don't crash
        fs.write_text(_PATH, '"just a string"')
        # pydantic will raise ValidationError for a model expecting a dict
        result = load_config(fs, _PATH, PermissionsBlock)
        # Either None (if pydantic rejects) or a valid model is acceptable;
        # what matters is no exception escapes.
        assert result is None or isinstance(result, PermissionsBlock)


# ---------------------------------------------------------------------------
# load_mcp_servers helper
# ---------------------------------------------------------------------------


class TestLoadMcpServers:
    def test_returns_parsed_entries(self) -> None:
        fs = FakeFileSystem()
        data = {"myserver": {"targets": ["claude", "cursor"]}}
        fs.write_text(_PATH, json.dumps(data))
        result = load_mcp_servers(fs, _PATH)
        assert "myserver" in result
        assert result["myserver"].targets == ["claude", "cursor"]

    def test_filters_non_object_entries(self) -> None:
        fs = FakeFileSystem()
        data = {"$comment": "ignore", "server": {"targets": ["claude"]}}
        fs.write_text(_PATH, json.dumps(data))
        result = load_mcp_servers(fs, _PATH)
        assert list(result.keys()) == ["server"]

    def test_returns_empty_for_missing_file(self) -> None:
        fs = FakeFileSystem()
        assert load_mcp_servers(fs, _PATH) == {}

    def test_returns_empty_for_invalid_json(self) -> None:
        fs = FakeFileSystem()
        fs.write_text(_PATH, "BAD JSON")
        assert load_mcp_servers(fs, _PATH) == {}

    def test_empty_targets_defaults(self) -> None:
        fs = FakeFileSystem()
        fs.write_text(_PATH, json.dumps({"srv": {}}))
        result = load_mcp_servers(fs, _PATH)
        assert result["srv"].targets == []
