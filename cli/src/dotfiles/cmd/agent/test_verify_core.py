"""Tests for AgentVerifyService (core/verify.py)."""

from pathlib import Path

from dotfiles.cmd.agent.verify import AgentVerifyService


def _make_svc(
    *,
    home: Path,
    dotfiles_dir: Path,
    which_map: dict[str, str] | None = None,
) -> AgentVerifyService:
    _map = which_map or {}
    return AgentVerifyService(
        home=home,
        dotfiles_dir=dotfiles_dir,
        which=lambda name: _map.get(name),
    )


# ---------------------------------------------------------------------------
# Path-level semantics
# ---------------------------------------------------------------------------


def test_missing_path_gives_missing_status(tmp_path: Path) -> None:
    svc = _make_svc(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles")
    result = svc._check("claude", "skills", tmp_path / "home" / ".claude" / "skills")
    assert result.status == "missing"
    assert ".claude/skills" in result.detail


def test_dir_with_skill_md_gives_present_n_skills(tmp_path: Path) -> None:
    d = tmp_path / "home" / ".claude" / "skills"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("# Skill")
    svc = _make_svc(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles")
    result = svc._check("claude", "skills", d)
    assert result.status == "present"
    assert "1 skills @" in result.detail


def test_dir_with_skill_md_in_subdir_counts_at_depth2(tmp_path: Path) -> None:
    d = tmp_path / "home" / ".claude" / "skills"
    sub = d / "foo"
    sub.mkdir(parents=True)
    (sub / "SKILL.md").write_text("# Skill")
    svc = _make_svc(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles")
    result = svc._check("claude", "skills", d)
    assert result.status == "present"
    assert "1 skills @" in result.detail


def test_dir_with_entries_but_no_skill_md_gives_present_n_entries(tmp_path: Path) -> None:
    d = tmp_path / "home" / ".claude" / "agents"
    d.mkdir(parents=True)
    (d / "agent1.md").write_text("# Agent")
    (d / "agent2.md").write_text("# Agent2")
    svc = _make_svc(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles")
    result = svc._check("claude", "subagents", d)
    assert result.status == "present"
    assert "2 entries @" in result.detail


def test_empty_dir_gives_empty_status(tmp_path: Path) -> None:
    d = tmp_path / "home" / ".claude" / "skills"
    d.mkdir(parents=True)
    svc = _make_svc(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles")
    result = svc._check("claude", "skills", d)
    assert result.status == "empty"
    assert "empty:" in result.detail


def test_file_path_gives_present_status(tmp_path: Path) -> None:
    p = tmp_path / "home" / ".claude.json"
    p.parent.mkdir(parents=True)
    p.write_text("{}")
    svc = _make_svc(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles")
    result = svc._check("claude", "MCP config", p)
    assert result.status == "present"
    assert result.detail == str(p)


# ---------------------------------------------------------------------------
# Gemini / Pi gating
# ---------------------------------------------------------------------------


def test_gemini_skipped_when_cli_absent(tmp_path: Path) -> None:
    svc = _make_svc(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles", which_map={})
    surfaces = svc._gemini_surfaces()
    assert len(surfaces) == 1
    assert surfaces[0].status == "skipped"
    assert "gemini" in surfaces[0].detail


def test_gemini_checked_when_cli_present(tmp_path: Path) -> None:
    h = tmp_path / "home"
    settings = h / ".gemini" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{}")
    svc = _make_svc(
        home=h,
        dotfiles_dir=tmp_path / "dotfiles",
        which_map={"gemini": "/usr/bin/gemini"},
    )
    surfaces = svc._gemini_surfaces()
    assert len(surfaces) == 2
    statuses = {s.label: s.status for s in surfaces}
    assert statuses["settings.json"] == "present"
    assert statuses["GEMINI.md"] == "missing"


def test_pi_skipped_when_cli_absent(tmp_path: Path) -> None:
    svc = _make_svc(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles", which_map={})
    surfaces = svc._pi_surfaces()
    assert len(surfaces) == 1
    assert surfaces[0].status == "skipped"
    assert "pi" in surfaces[0].detail


def test_pi_checked_when_cli_present(tmp_path: Path) -> None:
    h = tmp_path / "home"
    pi_agent = h / ".pi" / "agent"
    pi_agent.mkdir(parents=True)
    (pi_agent / "settings.json").write_text("{}")
    svc = _make_svc(
        home=h,
        dotfiles_dir=tmp_path / "dotfiles",
        which_map={"pi": "/usr/bin/pi"},
    )
    surfaces = svc._pi_surfaces()
    labels = [s.label for s in surfaces]
    assert "settings.json" in labels
    assert "models.json" in labels


# ---------------------------------------------------------------------------
# Full vendors() output structure
# ---------------------------------------------------------------------------


def test_vendors_returns_all_vendor_groups(tmp_path: Path) -> None:
    svc = _make_svc(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles")
    surfaces = svc.vendors()
    vendors_seen = {s.agent for s in surfaces}
    assert "claude" in vendors_seen
    assert "cursor" in vendors_seen
    assert "codex" in vendors_seen
    assert "gemini" in vendors_seen
    assert "pi" in vendors_seen


def test_claude_surfaces_count(tmp_path: Path) -> None:
    svc = _make_svc(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles")
    surfaces = svc._claude_surfaces()
    assert len(surfaces) == 6


def test_cursor_surfaces_count(tmp_path: Path) -> None:
    svc = _make_svc(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles")
    surfaces = svc._cursor_surfaces()
    assert len(surfaces) == 4


def test_codex_surfaces_count(tmp_path: Path) -> None:
    svc = _make_svc(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles")
    surfaces = svc._codex_surfaces()
    assert len(surfaces) == 7


def test_multiple_skill_md_files_counted(tmp_path: Path) -> None:
    d = tmp_path / "home" / ".claude" / "skills"
    d.mkdir(parents=True)
    # 1 at depth 1
    (d / "SKILL.md").write_text("# S1")
    sub = d / "bar"
    sub.mkdir()
    # 1 at depth 2
    (sub / "SKILL.md").write_text("# S2")
    svc = _make_svc(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles")
    result = svc._check("claude", "skills", d)
    assert result.status == "present"
    assert "2 skills @" in result.detail
