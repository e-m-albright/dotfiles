from typer.testing import CliRunner

from dotfiles_cli.cli.main import app
from tests.fakes import FakeProcessRunner, make_fake_context

runner = CliRunner()


def _runner_with_status(remote_login: str = "Off") -> FakeProcessRunner:
    r = FakeProcessRunner()
    r.script(("id", "-un"), stdout="evan\n")
    r.script(("scutil", "--get", "LocalHostName"), stdout="Evans-MBP-M4\n")
    r.script(("systemsetup", "-getremotelogin"), stdout=f"Remote Login: {remote_login}\n")
    r.script(("tailscale", "status"), exit_code=1)
    r.script(("mosh", "--version"), stdout="mosh 1.4.0\n")
    r.script(("zellij", "--version"), stdout="zellij 0.44.3\n")
    return r


def _flat(output: str) -> str:
    """Collapse Rich's line-wrapping so multi-line assertions work."""
    return " ".join(output.split())


def test_remote_setup_dry_run_prints_connection_command() -> None:
    fake = make_fake_context(runner=_runner_with_status(), interactive=True)
    result = runner.invoke(app, ["remote", "setup", "--dry-run"], obj=fake)
    assert result.exit_code == 0
    flat = _flat(result.output)
    assert "mosh --server=" in flat
    assert "zellij attach --create mobile" in flat


def test_remote_setup_session_flag_changes_command() -> None:
    fake = make_fake_context(runner=_runner_with_status(), interactive=True)
    result = runner.invoke(app, ["remote", "setup", "--dry-run", "--session", "work"], obj=fake)
    assert result.exit_code == 0
    assert "zellij attach --create work" in _flat(result.output)


def test_remote_setup_bad_key_exits_nonzero() -> None:
    fake = make_fake_context(runner=_runner_with_status(), interactive=True)
    result = runner.invoke(app, ["remote", "setup", "--add-key", "garbage"], obj=fake)
    assert result.exit_code != 0
    assert "does not look like" in result.output.lower() or "invalid" in result.output.lower()


def test_remote_disable_dry_run() -> None:
    fake = make_fake_context(runner=_runner_with_status("On"), interactive=True)
    result = runner.invoke(app, ["remote", "disable", "--dry-run", "--kill-sessions"], obj=fake)
    assert result.exit_code == 0
    assert "DRY RUN" in result.output
