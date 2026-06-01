"""CLI surface for dotfiles snapshot."""

from typer.testing import CliRunner

from dotfiles.cli.main import app
from tests.fakes import FakeProcessRunner, make_fake_context

runner = CliRunner()


def _ctx(tmp_path):
    proc = FakeProcessRunner()
    proc.script(("brew", "leaves"), stdout="git\n")
    proc.script(("brew", "list", "--cask", "-1"), stdout="cursor\n")
    return make_fake_context(
        runner=proc,
        home=tmp_path / "h",
        dotfiles_dir=tmp_path / "d",
        state_dir=tmp_path / "state",
    )


def test_snapshot_capture_writes_a_file(tmp_path):
    ctx = _ctx(tmp_path)
    result = runner.invoke(app, ["snapshot"], obj=ctx)
    assert result.exit_code == 0
    assert list((tmp_path / "state" / "snapshots").glob("*.json"))


def test_snapshot_ls_lists_captures(tmp_path):
    ctx = _ctx(tmp_path)
    runner.invoke(app, ["snapshot"], obj=ctx)
    result = runner.invoke(app, ["snapshot", "ls"], obj=ctx)
    assert result.exit_code == 0
    assert ".json" in result.stdout


def test_snapshot_diff_now_against_latest(tmp_path):
    ctx = _ctx(tmp_path)
    runner.invoke(app, ["snapshot"], obj=ctx)  # one saved snapshot
    result = runner.invoke(app, ["snapshot", "diff", "now"], obj=ctx)
    assert result.exit_code == 0
    # Same machine state -> no drift.
    assert "No drift" in result.stdout


def test_snapshot_diff_needs_two_when_no_args(tmp_path):
    ctx = _ctx(tmp_path)
    runner.invoke(app, ["snapshot"], obj=ctx)  # only one
    result = runner.invoke(app, ["snapshot", "diff"], obj=ctx)
    assert result.exit_code == 1
    assert "need at least two" in result.stdout.lower()
