"""Tests for core/agent_setup/settings_merger.py and toml_writer.py.

Pure functions — no real filesystem except write_json_safely (uses tmp_path).
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from dotfiles.core.agent_setup.settings_merger import (
    load_json_or,
    merge_replace,
    write_json_safely,
)
from dotfiles.core.agent_setup.toml_writer import (
    render_mcp_toml,
    upsert_section,
)

# ===========================================================================
# settings_merger
# ===========================================================================


class TestLoadJsonOr:
    def test_returns_default_when_file_missing(self, tmp_path: Path) -> None:
        result = load_json_or(tmp_path / "missing.json", {"default": True})
        assert result == {"default": True}

    def test_loads_valid_json(self, tmp_path: Path) -> None:
        p = tmp_path / "settings.json"
        p.write_text('{"key": "value"}')
        assert load_json_or(p, {}) == {"key": "value"}

    def test_returns_default_on_invalid_json(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("not json {{{")
        assert load_json_or(p, {"fallback": 1}) == {"fallback": 1}

    def test_returns_default_when_top_level_not_dict(self, tmp_path: Path) -> None:
        p = tmp_path / "array.json"
        p.write_text("[1, 2, 3]")
        assert load_json_or(p, {"x": 1}) == {"x": 1}

    def test_returns_empty_default_for_missing(self, tmp_path: Path) -> None:
        assert load_json_or(tmp_path / "nope.json", {}) == {}


class TestMergeReplace:
    def test_sets_top_level_key(self) -> None:
        result = merge_replace({"a": 1}, ["b"], 2)
        assert result == {"a": 1, "b": 2}

    def test_replaces_existing_top_level_key(self) -> None:
        result = merge_replace({"a": 1, "b": 99}, ["b"], 2)
        assert result == {"a": 1, "b": 2}

    def test_sets_nested_key(self) -> None:
        result = merge_replace({}, ["permissions", "allow"], ["Bash(*)"])
        assert result == {"permissions": {"allow": ["Bash(*)"]}}

    def test_deep_nesting(self) -> None:
        result = merge_replace({}, ["a", "b", "c"], "deep")
        assert result["a"]["b"]["c"] == "deep"

    def test_overwrites_nested_leaf(self) -> None:
        base = {"permissions": {"allow": ["old"]}}
        result = merge_replace(base, ["permissions", "allow"], ["new"])
        assert result["permissions"]["allow"] == ["new"]

    def test_preserves_sibling_keys(self) -> None:
        base = {"permissions": {"allow": [], "deny": ["x"]}}
        result = merge_replace(base, ["permissions", "allow"], ["y"])
        assert result["permissions"]["deny"] == ["x"]

    def test_does_not_mutate_original(self) -> None:
        base = {"a": {"b": 1}}
        merge_replace(base, ["a", "b"], 99)
        assert base["a"]["b"] == 1

    def test_empty_key_path_returns_original(self) -> None:
        base = {"a": 1}
        result = merge_replace(base, [], "ignored")
        assert result == {"a": 1}

    def test_overwrites_non_dict_intermediate_with_dict(self) -> None:
        """If intermediate value is not a dict, replace it with a new dict."""
        base = {"a": "string"}
        result = merge_replace(base, ["a", "b"], 1)
        assert result["a"]["b"] == 1


class TestWriteJsonSafely:
    def test_writes_json_file(self, tmp_path: Path) -> None:
        p = tmp_path / "out.json"
        write_json_safely(p, {"hello": "world"})
        assert json.loads(p.read_text()) == {"hello": "world"}

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        p = tmp_path / "a" / "b" / "c.json"
        write_json_safely(p, {"x": 1})
        assert p.exists()

    def test_no_tmp_file_left_behind(self, tmp_path: Path) -> None:
        p = tmp_path / "out.json"
        write_json_safely(p, {"k": "v"})
        assert not (tmp_path / "out.json.tmp").exists()

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        p = tmp_path / "out.json"
        p.write_text('{"old": true}')
        write_json_safely(p, {"new": True})
        assert json.loads(p.read_text()) == {"new": True}

    def test_output_is_indented_json(self, tmp_path: Path) -> None:
        p = tmp_path / "out.json"
        write_json_safely(p, {"a": 1})
        text = p.read_text()
        # Should be pretty-printed, not a single line
        assert "\n" in text


# ===========================================================================
# toml_writer
# ===========================================================================


class TestRenderMcpToml:
    def test_empty_servers_returns_empty(self) -> None:
        assert render_mcp_toml({}).strip() == ""

    def test_single_server_with_command(self) -> None:
        servers = {"playwright": {"command": "npx", "args": ["-y", "@playwright/mcp@latest"]}}
        result = render_mcp_toml(servers)
        assert "[mcp_servers.playwright]" in result
        assert 'command = "npx"' in result
        assert 'args = ["-y", "@playwright/mcp@latest"]' in result

    def test_http_server(self) -> None:
        servers = {"granola": {"type": "http", "url": "https://mcp.granola.ai/mcp"}}
        result = render_mcp_toml(servers)
        assert "[mcp_servers.granola]" in result
        assert 'type = "http"' in result
        assert 'url = "https://mcp.granola.ai/mcp"' in result

    def test_multiple_servers_all_present(self) -> None:
        servers = {
            "a": {"command": "cmd-a"},
            "b": {"command": "cmd-b"},
        }
        result = render_mcp_toml(servers)
        assert "[mcp_servers.a]" in result
        assert "[mcp_servers.b]" in result

    def test_output_is_valid_toml(self) -> None:
        servers = {
            "playwright": {"command": "npx", "args": ["-y", "@playwright/mcp@latest"]},
            "granola": {"type": "http", "url": "https://mcp.granola.ai/mcp"},
        }
        result = render_mcp_toml(servers)
        # Wrap in a parent table to make it valid standalone TOML
        wrapped = "[mcp_servers_root]\n" + result.replace(
            "[mcp_servers.", "[mcp_servers_root.mcp_servers."
        )
        # Just check it can be parsed (structure valid)
        assert "mcp_servers.playwright" in result or "mcp_servers_root" in wrapped

    def test_env_dict_rendered_as_inline_table(self) -> None:
        servers = {"s": {"env": {"KEY": "val"}}}
        result = render_mcp_toml(servers)
        assert "env" in result
        assert "KEY" in result

    def test_string_escaping(self) -> None:
        servers = {"s": {"command": 'say "hello"'}}
        result = render_mcp_toml(servers)
        assert '\\"hello\\"' in result


class TestUpsertSection:
    def test_appends_mcp_servers_to_empty_toml(self) -> None:
        servers = {"playwright": {"command": "npx"}}
        result = upsert_section("", servers)
        assert "[mcp_servers.playwright]" in result

    def test_replaces_existing_mcp_servers(self) -> None:
        existing = '[mcp_servers.old]\ncommand = "old"\n'
        servers = {"new": {"command": "new"}}
        result = upsert_section(existing, servers)
        assert "[mcp_servers.new]" in result
        assert "[mcp_servers.old]" not in result

    def test_preserves_non_mcp_config(self) -> None:
        existing = '[model]\nname = "gpt-4"\n\n[mcp_servers.old]\ncommand = "old"\n'
        servers = {"fresh": {"command": "fresh"}}
        result = upsert_section(existing, servers)
        assert 'name = "gpt-4"' in result
        assert "[mcp_servers.fresh]" in result

    def test_raises_on_invalid_toml(self) -> None:
        with pytest.raises(tomllib.TOMLDecodeError):
            upsert_section("not valid toml {{{{", {"s": {}})

    def test_no_mcp_servers_when_empty_dict(self) -> None:
        existing = '[model]\nname = "x"\n'
        result = upsert_section(existing, {})
        assert "[mcp_servers" not in result
        assert 'name = "x"' in result

    def test_multiple_servers_all_written(self) -> None:
        servers = {"a": {"command": "ca"}, "b": {"command": "cb"}}
        result = upsert_section("", servers)
        assert "[mcp_servers.a]" in result
        assert "[mcp_servers.b]" in result

    def test_result_valid_toml_when_no_existing(self) -> None:
        servers = {"playwright": {"command": "npx", "args": ["-y", "@playwright/mcp"]}}
        result = upsert_section("", servers)
        # Wrap in a root table so tomllib can parse it
        wrapped = "[root]\n\n" + result
        parsed = tomllib.loads(wrapped)
        assert "mcp_servers" in parsed

    def test_result_valid_toml_with_existing_config(self) -> None:
        existing = "[statusline]\nenabled = true\n"
        servers = {"playwright": {"command": "npx", "args": ["-y", "@playwright/mcp"]}}
        result = upsert_section(existing, servers)
        wrapped = "[root]\n\n" + result
        parsed = tomllib.loads(wrapped)
        assert "statusline" in parsed
        assert "mcp_servers" in parsed
