"""CLI surface for dotfiles fleet."""

from typer.testing import CliRunner

from dotfiles.cli.main import app
from tests.fakes import FakeProcessRunner, make_fake_context

runner = CliRunner()


def test_fleet_lists_sessions_and_notes_ledger_only_vendors(tmp_path):
    home = tmp_path / "home"
    d = home / ".claude/projects/-home-evan-dotfiles/abc.jsonl"
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text("{}\n")
    # leave mtime as "now" so it is within threshold
    proc = FakeProcessRunner()
    proc.script(("git", "worktree", "list", "--porcelain"), stdout="")
    ctx = make_fake_context(runner=proc, home=home, state_dir=tmp_path / "state")
    result = runner.invoke(app, ["fleet", "--all"], obj=ctx)
    assert result.exit_code == 0
    assert "claude" in result.stdout
    assert "cursor/pi" in result.stdout.lower()  # ledger-only note


def test_fleet_json_outputs_array(tmp_path):
    proc = FakeProcessRunner()
    proc.script(("git", "worktree", "list", "--porcelain"), stdout="")
    ctx = make_fake_context(runner=proc, home=tmp_path / "home", state_dir=tmp_path / "state")
    result = runner.invoke(app, ["fleet", "--json"], obj=ctx)
    assert result.exit_code == 0
    assert result.stdout.strip().startswith("[")
