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


def test_na_surface_is_skipped(tmp_path: Path) -> None:
    # Gemini has no skills surface → uniform row, status n/a (skipped).
    svc = _make_svc(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles")
    g_skills = next(s for s in svc.vendors() if s.agent == "gemini" and s.label == "skills")
    assert g_skills.status == "skipped"
    assert g_skills.quantity == "n/a"


def test_present_and_missing_surfaces_for_an_agent(tmp_path: Path) -> None:
    h = tmp_path / "home"
    settings = h / ".gemini" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{}")  # GEMINI.md deliberately absent
    by_label = {
        s.label: s
        for s in _make_svc(home=h, dotfiles_dir=tmp_path / "dotfiles").vendors()
        if s.agent == "gemini"
    }
    assert by_label["settings"].status == "present"
    assert by_label["instructions"].status == "missing"


# ---------------------------------------------------------------------------
# Full vendors() output structure — uniform checklist for every agent
# ---------------------------------------------------------------------------


def test_vendors_returns_all_vendor_groups(tmp_path: Path) -> None:
    svc = _make_svc(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles")
    surfaces = svc.vendors()
    vendors_seen = {s.agent for s in surfaces}
    assert vendors_seen == {"claude", "cursor", "codex", "gemini", "pi"}


def test_every_agent_has_the_same_attribute_checklist(tmp_path: Path) -> None:
    from dotfiles.cmd.agent.verify import _ATTRIBUTES

    surfaces = _make_svc(home=tmp_path / "home", dotfiles_dir=tmp_path / "dotfiles").vendors()
    for agent in ("claude", "cursor", "codex", "gemini", "pi"):
        labels = [s.label for s in surfaces if s.agent == agent]
        assert labels == list(_ATTRIBUTES)


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
