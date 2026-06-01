from typer.testing import CliRunner

from dotfiles_cli.cli.main import app

runner = CliRunner()


def test_help_lists_top_level_command_tree() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("remote", "session", "doctor", "brew", "agent", "verify", "scaffold", "llm"):
        assert command in result.output


def test_version_command() -> None:
    from dotfiles_cli import __version__

    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_session_alias_sesh_is_registered() -> None:
    result = runner.invoke(app, ["sesh", "--help"])
    assert result.exit_code == 0


def test_root_callback_builds_context_when_none_injected() -> None:
    # version command works without an injected obj (callback builds the real context)
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0


def test_session_and_sesh_share_real_commands() -> None:
    for name in ("session", "sesh"):
        result = runner.invoke(app, [name, "ls", "--help"])
        assert result.exit_code == 0
