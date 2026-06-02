"""CLI surface for dotfiles agent verify."""

from typer.testing import CliRunner

from dotfiles.app.main import app
from dotfiles.testing.fakes import make_fake_context

runner = CliRunner()


def test_agent_verify_offline_runs(tmp_path):
    ctx = make_fake_context(home=tmp_path / "h", dotfiles_dir=tmp_path / "d")
    result = runner.invoke(app, ["agent", "global", "verify", "--offline"], obj=ctx)
    assert result.exit_code == 0
    assert "claude" in result.stdout
