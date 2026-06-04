"""Reading what's running in a zellij session from its session_info cache."""

from pathlib import Path

from dotfiles.cmd.session.session_info import (
    parse_pane_titles,
    parse_session_cwd,
    session_cwd,
    session_program_titles,
    zellij_cache_root,
)


def test_parse_session_cwd_reads_top_level_cwd() -> None:
    layout = (
        'layout {\n    cwd "/Users/evan/dotfiles"\n    pane {\n        cwd "/tmp/other"\n    }\n}\n'
    )
    assert parse_session_cwd(layout) == "/Users/evan/dotfiles"


def test_parse_session_cwd_none_when_absent() -> None:
    assert parse_session_cwd("layout {\n    pane { }\n}\n") is None


# Trimmed from a real session-metadata.kdl: one terminal pane + two plugin panes
# (chrome) + one suppressed plugin overlay. Only the terminal pane should surface.
_METADATA = """\
name "banana"
tabs {
    tab {
        position 0
        name "Tab #1"
    }
}
panes {
    pane {
        id 0
        is_plugin false
        title "✳ Claude Code"
        exited false
        is_suppressed false
    }
    pane {
        id 1
        is_plugin true
        title "tab-bar"
        plugin_url "tab-bar"
    }
    pane {
        id 2
        is_plugin true
        title "status-bar"
        plugin_url "status-bar"
    }
    pane {
        id 0
        is_plugin true
        is_suppressed true
        title "(.) - zellij:link"
        plugin_url "zellij:link"
    }
}
connected_clients 1
"""


def test_parse_pane_titles_keeps_only_real_terminal_panes():
    assert parse_pane_titles(_METADATA) == ["✳ Claude Code"]


def test_parse_pane_titles_skips_exited_panes():
    metadata = """\
panes {
    pane { id 0 is_plugin false exited true title "old vim" }
    pane { id 1 is_plugin false exited false title "zsh" }
}
"""
    assert parse_pane_titles(metadata) == ["zsh"]


def test_parse_pane_titles_empty_when_no_panes_section():
    assert parse_pane_titles('name "x"\n') == []


def test_session_program_titles_reads_from_cache(tmp_path: Path):
    info = tmp_path / "contract_version_1" / "session_info" / "banana"
    info.mkdir(parents=True)
    (info / "session-metadata.kdl").write_text(_METADATA)
    assert session_program_titles(cache_root=tmp_path, name="banana") == ["✳ Claude Code"]


def test_session_cwd_reads_from_cache(tmp_path: Path):
    info = tmp_path / "contract_version_1" / "session_info" / "banana"
    info.mkdir(parents=True)
    (info / "session-layout.kdl").write_text('layout {\n    cwd "/Users/evan/blog"\n}\n')
    assert session_cwd(cache_root=tmp_path, name="banana") == "/Users/evan/blog"


def test_session_cwd_degrades_to_none_when_missing(tmp_path: Path):
    assert session_cwd(cache_root=tmp_path, name="ghost") is None


def test_session_program_titles_degrades_to_empty_when_missing(tmp_path: Path):
    assert session_program_titles(cache_root=tmp_path, name="ghost") == []
    assert session_program_titles(cache_root=tmp_path / "nope", name="ghost") == []


def test_zellij_cache_root_is_os_specific(monkeypatch):
    home = Path("/home/evan")
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    assert zellij_cache_root(home, "linux") == home / ".cache" / "zellij"
    assert (
        zellij_cache_root(home, "darwin")
        == home / "Library" / "Caches" / "org.Zellij-Contributors.Zellij"
    )
    monkeypatch.setenv("XDG_CACHE_HOME", "/custom/cache")
    assert zellij_cache_root(home, "linux") == Path("/custom/cache") / "zellij"
