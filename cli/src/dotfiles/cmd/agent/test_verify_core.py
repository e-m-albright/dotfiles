"""Tests for the vendor-page projection (verify.py) over the fleet model."""

from __future__ import annotations

from pathlib import Path

from dotfiles.agent import AGENTS
from dotfiles.cmd.agent.fleet import build_fleet
from dotfiles.cmd.agent.verify import _SURFACE_ORDER, vendor_surfaces


def _surfaces(tmp_path: Path):
    home = tmp_path / "home"
    repo = tmp_path / "dotfiles"
    fleet = build_fleet(home=home, dotfiles_dir=repo)
    return vendor_surfaces(fleet, home=home, dotfiles_dir=repo)


def test_vendors_returns_all_vendor_groups(tmp_path: Path) -> None:
    assert {s.agent for s in _surfaces(tmp_path)} == set(AGENTS)


def test_every_agent_has_the_same_surface_checklist(tmp_path: Path) -> None:
    surfaces = _surfaces(tmp_path)
    expected = list(_SURFACE_ORDER)
    for agent in AGENTS:
        labels = [s.label for s in surfaces if s.agent == agent]
        assert labels == expected


def test_missing_paths_read_missing_on_empty_tree(tmp_path: Path) -> None:
    by = {(s.agent, s.label): s for s in _surfaces(tmp_path)}
    assert by[("claude", "skills")].status == "missing"
    assert by[("gemini", "skills")].status == "missing"


def test_deployed_skills_counted(tmp_path: Path) -> None:
    skills = tmp_path / "home" / ".claude" / "skills"
    for name in ("alpha", "beta"):
        (skills / name).mkdir(parents=True)
    by = {(s.agent, s.label): s for s in _surfaces(tmp_path)}
    cell = by[("claude", "skills")]
    assert cell.status == "present"
    assert cell.quantity == "2 skills"


def test_empty_skill_dir_reads_empty(tmp_path: Path) -> None:
    (tmp_path / "home" / ".claude" / "skills").mkdir(parents=True)
    by = {(s.agent, s.label): s for s in _surfaces(tmp_path)}
    assert by[("claude", "skills")].status == "empty"


def test_subagents_counted_as_md_files(tmp_path: Path) -> None:
    agents = tmp_path / "home" / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "debugger.md").write_text("# d")
    by = {(s.agent, s.label): s for s in _surfaces(tmp_path)}
    cell = by[("claude", "subagents")]
    assert cell.status == "present"
    assert cell.quantity == "1 agents"


def test_local_stances_show_their_reason_not_bare_na(tmp_path: Path) -> None:
    by = {(s.agent, s.label): s for s in _surfaces(tmp_path)}
    gem_sub = by[("gemini", "subagents")]
    assert gem_sub.status == "skipped"
    assert gem_sub.quantity == "local-only"
    assert "workspace" in gem_sub.detail
    hermes_rules = by[("hermes", "rules")]
    assert hermes_rules.status == "skipped"
    assert "AGENTS.md" in hermes_rules.detail


def test_native_stance_reads_present_with_note(tmp_path: Path) -> None:
    by = {(s.agent, s.label): s for s in _surfaces(tmp_path)}
    agy_status = by[("gemini", "statusline")]
    assert agy_status.status == "present"
    assert agy_status.quantity == "native"


def test_none_stance_reads_na(tmp_path: Path) -> None:
    by = {(s.agent, s.label): s for s in _surfaces(tmp_path)}
    assert by[("pi", "mcp")].status == "skipped"
    assert by[("pi", "mcp")].quantity == "n/a"
    assert by[("hermes", "settings")].status == "skipped"


def test_hooks_quantity_reports_wired_intents(tmp_path: Path) -> None:
    settings = tmp_path / "home" / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text('{"hooks": {"x": "guard-sensitive-file.sh; notify.sh"}}')
    by = {(s.agent, s.label): s for s in _surfaces(tmp_path)}
    cell = by[("claude", "hooks")]
    # 2 of 4 intents wired → partial, surfaced as ○ with the true count.
    assert cell.status == "empty"
    assert cell.quantity == "2 hooks wired"


def test_cursor_rules_probe_is_repo_rooted(tmp_path: Path) -> None:
    mdc = tmp_path / "dotfiles" / "ai" / "agents" / "cursor" / "rules"
    mdc.mkdir(parents=True)
    (mdc / "shared-rules.mdc").write_text("---\n---\n")
    by = {(s.agent, s.label): s for s in _surfaces(tmp_path)}
    cell = by[("cursor", "rules")]
    assert cell.status == "present"
    assert cell.quantity == "1 .mdc"
