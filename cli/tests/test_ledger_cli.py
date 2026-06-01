"""CLI surface for dotfiles ledger."""

from typer.testing import CliRunner

from dotfiles.cli.main import app
from dotfiles.core.ledger import read
from tests.fakes import make_fake_context

runner = CliRunner()


def test_ledger_log_appends(tmp_path):
    ctx = make_fake_context(state_dir=tmp_path / "state")
    result = runner.invoke(
        app,
        [
            "ledger",
            "log",
            "--session",
            "s1",
            "--vendor",
            "claude",
            "--cwd",
            "/x",
            "--task",
            "work",
            "--status",
            "active",
        ],
        obj=ctx,
    )
    assert result.exit_code == 0
    entries = read(tmp_path / "state")
    assert entries[0].session_id == "s1"
    assert entries[0].task == "work"


def test_ledger_ls_shows_entries(tmp_path):
    ctx = make_fake_context(state_dir=tmp_path / "state")
    runner.invoke(
        app,
        [
            "ledger",
            "log",
            "--session",
            "s1",
            "--vendor",
            "claude",
            "--cwd",
            "/x",
            "--status",
            "active",
        ],
        obj=ctx,
    )
    result = runner.invoke(app, ["ledger", "ls"], obj=ctx)
    assert result.exit_code == 0
    assert "s1" in result.stdout
