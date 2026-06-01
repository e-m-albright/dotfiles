"""Snapshot models + core logic."""

from datetime import datetime
from pathlib import Path

from dotfiles.core.models import (
    AgentOverview,
    BrewState,
    HookRow,
    McpRow,
    RulesSummary,
    SkillsSummary,
    Snapshot,
    SymlinkState,
)
from dotfiles.core.snapshot import (
    agent_config_hashes,
    collect_brew,
    collect_runtimes,
    collect_symlinks,
)
from tests.fakes import FakeProcessRunner, write_tree


def test_snapshot_round_trips_through_json():
    snap = Snapshot(
        taken_at=datetime(2026, 6, 1, 14, 2, 9),
        brew=BrewState(leaves=("git", "jq"), casks=("cursor",)),
        runtimes={"node": "v22.3.0", "uv": "uv 0.5.0"},
        symlinks=(SymlinkState(path="/home/e/.zshrc", target="/d/shell/.zshrc", ok=True),),
        agent_config={"claude": "abc123"},
    )
    restored = Snapshot.model_validate_json(snap.model_dump_json())
    assert restored == snap


def test_collect_brew_reads_leaves_and_casks():
    runner = FakeProcessRunner()
    runner.script(("brew", "leaves"), stdout="git\njq\n")
    runner.script(("brew", "list", "--cask", "-1"), stdout="cursor\nzed\n")
    state = collect_brew(runner)
    assert state.leaves == ("git", "jq")
    assert state.casks == ("cursor", "zed")


def test_collect_runtimes_skips_absent_tools():
    runner = FakeProcessRunner()
    runner.script(("node", "--version"), stdout="v22.3.0\n")
    present = {"node", "uv"}
    runner.script(("uv", "--version"), stdout="uv 0.5.0\n")
    runtimes = collect_runtimes(runner, which=lambda c: c if c in present else None)
    assert runtimes == {"node": "v22.3.0", "uv": "uv 0.5.0"}


def test_collect_symlinks_flags_ok_and_broken(tmp_path):
    home = tmp_path / "home"
    dotfiles = tmp_path / "dotfiles"
    write_tree(dotfiles, {"shell/.zshrc": "rc", "git/.gitconfig": "gc", "shell/.zprofile": "zp"})
    home.mkdir()
    (home / ".zshrc").symlink_to(dotfiles / "shell" / ".zshrc")  # ok
    # .gitconfig + .zprofile absent -> ok=False, target=""
    states = collect_symlinks(home=home, dotfiles_dir=dotfiles)
    by_name = {Path(s.path).name: s for s in states}
    assert by_name[".zshrc"].ok is True
    assert by_name[".zshrc"].target == str(dotfiles / "shell" / ".zshrc")
    assert by_name[".gitconfig"].ok is False
    assert by_name[".gitconfig"].target == ""


def _overview() -> AgentOverview:
    return AgentOverview(
        mcp=(McpRow(server="granola", claude=True, cursor=False, codex=False, gemini=False),),
        hooks=(HookRow(event="PostToolUse", claude=True, cursor=True, codex=False),),
        skills=SkillsSummary(canonical_skills=21, claude_deployed=21, shared_deployed=21),
        agents=(),
        rules=RulesSummary(canonical_rules=31, claude_deployed=31, cursor_deployed=31),
        permissions=(),
    )


def test_agent_config_hashes_are_stable_and_per_vendor():
    a = agent_config_hashes(_overview())
    b = agent_config_hashes(_overview())
    assert a == b  # deterministic
    assert set(a) == {"claude", "cursor", "codex", "gemini"}
    assert all(isinstance(v, str) and v for v in a.values())


def test_agent_config_hash_changes_when_mcp_changes():
    base = agent_config_hashes(_overview())
    changed_overview = _overview().model_copy(
        update={
            "mcp": (
                McpRow(server="granola", claude=False, cursor=False, codex=False, gemini=False),
            )
        }
    )
    changed = agent_config_hashes(changed_overview)
    assert changed["claude"] != base["claude"]
