"""Snapshot models + core logic."""

from datetime import datetime
from pathlib import Path

from dotfiles.cmd.agent.models import AgentOverview, AgentPresenceRow, RulesSummary, SkillsSummary
from dotfiles.cmd.snapshot.models import BrewState, RuntimeChange, Snapshot, SymlinkState
from dotfiles.cmd.snapshot.service import (
    agent_config_hashes,
    capture,
    collect_brew,
    collect_runtimes,
    collect_symlinks,
    diff,
    list_snapshots,
    load_snapshot,
    write_snapshot,
)
from dotfiles.testing.fakes import FakeProcessRunner, write_tree


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
        mcp=(
            AgentPresenceRow(
                label="granola",
                cells={
                    "claude": True,
                    "cursor": False,
                    "codex": False,
                    "gemini": False,
                    "pi": False,
                },
            ),
        ),
        hooks=(
            AgentPresenceRow(
                label="PostToolUse",
                cells={
                    "claude": True,
                    "cursor": True,
                    "codex": False,
                    "gemini": False,
                    "pi": False,
                },
            ),
        ),
        skills=SkillsSummary(
            canonical_skills=21,
            deployed={"claude": 21, "cursor": 21, "codex": 21},
        ),
        agents=(),
        rules=RulesSummary(canonical_rules=31, claude_deployed=31, cursor_deployed=31),
        permissions=(),
    )


def test_agent_config_hashes_are_stable_and_per_vendor():
    a = agent_config_hashes(_overview())
    b = agent_config_hashes(_overview())
    assert a == b  # deterministic
    assert set(a) == {"claude", "cursor", "codex", "gemini", "pi", "hermes"}
    assert all(isinstance(v, str) and v for v in a.values())


def test_agent_config_hash_changes_when_mcp_changes():
    base = agent_config_hashes(_overview())
    changed_overview = _overview().model_copy(
        update={
            "mcp": (
                AgentPresenceRow(
                    label="granola",
                    cells={
                        "claude": False,
                        "cursor": False,
                        "codex": False,
                        "gemini": False,
                        "pi": False,
                        "hermes": False,
                    },
                ),
            )
        }
    )
    changed = agent_config_hashes(changed_overview)
    assert changed["claude"] != base["claude"]


def _scripted_runner() -> FakeProcessRunner:
    runner = FakeProcessRunner()
    runner.script(("brew", "leaves"), stdout="git\n")
    runner.script(("brew", "list", "--cask", "-1"), stdout="cursor\n")
    runner.script(("node", "--version"), stdout="v22.3.0\n")
    return runner


def test_capture_builds_a_snapshot(tmp_path):
    runner = _scripted_runner()
    snap = capture(
        runner,
        dotfiles_dir=tmp_path / "d",
        home=tmp_path / "h",
        taken_at=datetime(2026, 6, 1, 9, 0, 0),
        which=lambda c: c if c == "node" else None,
    )
    assert snap.brew.leaves == ("git",)
    assert snap.runtimes == {"node": "v22.3.0"}
    assert set(snap.agent_config) == {"claude", "cursor", "codex", "gemini", "pi", "hermes"}


def test_write_then_load_and_list(tmp_path):
    runner = _scripted_runner()
    snap = capture(
        runner,
        dotfiles_dir=tmp_path / "d",
        home=tmp_path / "h",
        taken_at=datetime(2026, 6, 1, 9, 0, 0),
        which=lambda c: None,
    )
    state_dir = tmp_path / "state"
    path = write_snapshot(state_dir, snap)
    assert path.name == "2026-06-01T09-00-00.json"
    assert load_snapshot(path).taken_at == snap.taken_at
    assert list_snapshots(state_dir) == [path]


def _snap(*, leaves, runtimes, symlinks, agent_config, ts=datetime(2026, 6, 1)) -> Snapshot:
    return Snapshot(
        taken_at=ts,
        brew=BrewState(leaves=leaves, casks=()),
        runtimes=runtimes,
        symlinks=symlinks,
        agent_config=agent_config,
    )


def test_diff_reports_each_category():
    old = _snap(
        leaves=("git", "jq"),
        runtimes={"node": "v22.0.0"},
        symlinks=(SymlinkState(path="/h/.zshrc", target="/d/shell/.zshrc", ok=True),),
        agent_config={"claude": "aaa", "codex": "ccc"},
    )
    new = _snap(
        leaves=("git", "ripgrep"),
        runtimes={"node": "v22.3.0"},
        symlinks=(SymlinkState(path="/h/.zshrc", target="/somewhere/else", ok=False),),
        agent_config={"claude": "zzz", "codex": "ccc"},
    )
    d = diff(old, new)
    assert d.brew_added == ("ripgrep",)
    assert d.brew_removed == ("jq",)
    assert d.runtimes_changed == (RuntimeChange(name="node", old="v22.0.0", new="v22.3.0"),)
    assert d.symlinks_changed[0].broke is True
    assert d.agent_config_changed == ("claude",)
    assert d.is_empty is False


def test_diff_of_identical_snapshots_is_empty():
    snap = _snap(
        leaves=("git",), runtimes={"node": "v22"}, symlinks=(), agent_config={"claude": "x"}
    )
    assert diff(snap, snap).is_empty is True
