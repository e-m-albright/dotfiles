from typer.testing import CliRunner

from dotfiles.app.main import app

runner = CliRunner()


def test_help_lists_top_level_command_tree() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("remote", "session", "doctor", "brew", "agent", "benchmark"):
        assert command in result.output


def test_session_alias_sesh_is_removed() -> None:
    # `sesh` was retired in favour of the full `session` spelling.
    result = runner.invoke(app, ["sesh", "--help"])
    assert result.exit_code != 0


def test_root_callback_builds_context_when_none_injected() -> None:
    # a command works without an injected obj (callback builds the real context)
    result = runner.invoke(app, ["session", "ls", "--help"])
    assert result.exit_code == 0


def test_session_command_exposes_real_subcommands() -> None:
    result = runner.invoke(app, ["session", "ls", "--help"])
    assert result.exit_code == 0
