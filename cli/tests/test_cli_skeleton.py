from typer.testing import CliRunner

from dotfiles_cli.cli.main import app

runner = CliRunner()


def test_help_lists_top_level_command_tree() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("remote", "session", "doctor", "brew", "agent", "verify", "scaffold", "llm"):
        assert command in result.output


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_session_alias_sesh_is_registered() -> None:
    result = runner.invoke(app, ["sesh", "--help"])
    assert result.exit_code == 0
