"""Tests for VendorVerifyService (core/verify.py)."""

from pathlib import Path

from dotfiles.core.verify import VendorVerifyService
from tests.fakes import FakeFileSystem


def _make_svc(
    fs: FakeFileSystem,
    *,
    home: Path = Path("/home/evan"),
    dotfiles_dir: Path = Path("/home/evan/dotfiles"),
    which_map: dict[str, str] | None = None,
) -> VendorVerifyService:
    _map = which_map or {}
    return VendorVerifyService(
        fs=fs,
        home=home,
        dotfiles_dir=dotfiles_dir,
        which=lambda name: _map.get(name),
    )


# ---------------------------------------------------------------------------
# Path-level semantics
# ---------------------------------------------------------------------------


def test_missing_path_gives_missing_status() -> None:
    fs = FakeFileSystem()
    svc = _make_svc(fs)
    result = svc._check("claude", "skills", Path("/home/evan/.claude/skills"))
    assert result.status == "missing"
    assert result.detail == "/home/evan/.claude/skills"


def test_dir_with_skill_md_gives_present_n_skills() -> None:
    fs = FakeFileSystem()
    d = Path("/home/evan/.claude/skills")
    fs.mkdir(d)
    fs.write_text(d / "SKILL.md", "# Skill")
    svc = _make_svc(fs)
    result = svc._check("claude", "skills", d)
    assert result.status == "present"
    assert "1 skills @" in result.detail


def test_dir_with_skill_md_in_subdir_counts_at_depth2() -> None:
    fs = FakeFileSystem()
    d = Path("/home/evan/.claude/skills")
    sub = d / "foo"
    fs.mkdir(d)
    fs.mkdir(sub)
    fs.write_text(sub / "SKILL.md", "# Skill")
    svc = _make_svc(fs)
    result = svc._check("claude", "skills", d)
    assert result.status == "present"
    assert "1 skills @" in result.detail


def test_dir_with_entries_but_no_skill_md_gives_present_n_entries() -> None:
    fs = FakeFileSystem()
    d = Path("/home/evan/.claude/agents")
    fs.mkdir(d)
    fs.write_text(d / "agent1.md", "# Agent")
    fs.write_text(d / "agent2.md", "# Agent2")
    svc = _make_svc(fs)
    result = svc._check("claude", "subagents", d)
    assert result.status == "present"
    assert "2 entries @" in result.detail


def test_empty_dir_gives_empty_status() -> None:
    fs = FakeFileSystem()
    d = Path("/home/evan/.claude/skills")
    fs.mkdir(d)
    svc = _make_svc(fs)
    result = svc._check("claude", "skills", d)
    assert result.status == "empty"
    assert "empty:" in result.detail


def test_file_path_gives_present_status() -> None:
    fs = FakeFileSystem()
    p = Path("/home/evan/.claude.json")
    fs.write_text(p, "{}")
    svc = _make_svc(fs)
    result = svc._check("claude", "MCP config", p)
    assert result.status == "present"
    assert result.detail == str(p)


# ---------------------------------------------------------------------------
# Gemini / Pi gating
# ---------------------------------------------------------------------------


def test_gemini_skipped_when_cli_absent() -> None:
    fs = FakeFileSystem()
    svc = _make_svc(fs, which_map={})
    surfaces = svc._gemini_surfaces()
    assert len(surfaces) == 1
    assert surfaces[0].status == "skipped"
    assert "gemini" in surfaces[0].detail


def test_gemini_checked_when_cli_present() -> None:
    fs = FakeFileSystem()
    # settings.json exists, GEMINI.md missing
    h = Path("/home/evan")
    fs.write_text(h / ".gemini" / "settings.json", "{}")
    svc = _make_svc(fs, which_map={"gemini": "/usr/bin/gemini"})
    surfaces = svc._gemini_surfaces()
    assert len(surfaces) == 2
    statuses = {s.label: s.status for s in surfaces}
    assert statuses["settings.json"] == "present"
    assert statuses["GEMINI.md"] == "missing"


def test_pi_skipped_when_cli_absent() -> None:
    fs = FakeFileSystem()
    svc = _make_svc(fs, which_map={})
    surfaces = svc._pi_surfaces()
    assert len(surfaces) == 1
    assert surfaces[0].status == "skipped"
    assert "pi" in surfaces[0].detail


def test_pi_checked_when_cli_present() -> None:
    fs = FakeFileSystem()
    h = Path("/home/evan")
    pi_agent = h / ".pi" / "agent"
    fs.write_text(pi_agent / "settings.json", "{}")
    svc = _make_svc(fs, which_map={"pi": "/usr/bin/pi"})
    surfaces = svc._pi_surfaces()
    labels = [s.label for s in surfaces]
    assert "settings.json" in labels
    assert "models.json" in labels


# ---------------------------------------------------------------------------
# Full vendors() output structure
# ---------------------------------------------------------------------------


def test_vendors_returns_all_vendor_groups() -> None:
    fs = FakeFileSystem()
    svc = _make_svc(fs)
    surfaces = svc.vendors()
    vendors_seen = {s.vendor for s in surfaces}
    assert "claude" in vendors_seen
    assert "cursor" in vendors_seen
    assert "codex" in vendors_seen
    assert "gemini" in vendors_seen
    assert "pi" in vendors_seen


def test_claude_surfaces_count() -> None:
    fs = FakeFileSystem()
    svc = _make_svc(fs)
    surfaces = svc._claude_surfaces()
    assert len(surfaces) == 6


def test_cursor_surfaces_count() -> None:
    fs = FakeFileSystem()
    svc = _make_svc(fs)
    surfaces = svc._cursor_surfaces()
    assert len(surfaces) == 4


def test_codex_surfaces_count() -> None:
    fs = FakeFileSystem()
    svc = _make_svc(fs)
    surfaces = svc._codex_surfaces()
    assert len(surfaces) == 7


def test_multiple_skill_md_files_counted() -> None:
    fs = FakeFileSystem()
    d = Path("/home/evan/.claude/skills")
    fs.mkdir(d)
    # 2 at depth 1
    fs.write_text(d / "SKILL.md", "# S1")
    sub = d / "bar"
    fs.mkdir(sub)
    # 1 at depth 2
    fs.write_text(sub / "SKILL.md", "# S2")
    svc = _make_svc(fs)
    result = svc._check("claude", "skills", d)
    assert result.status == "present"
    assert "2 skills @" in result.detail
