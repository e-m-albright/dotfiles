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
    """Collapse Rich's line-wrapping so multi-line assertions work (DRY-RUN step messages only)."""
    return " ".join(output.split())


def _mosh_line(output: str) -> str:
    """Return the single line containing the mosh command; fail if it was wrapped."""
    lines = [ln for ln in output.splitlines() if ln.startswith("mosh --server=")]
    assert len(lines) == 1, f"mosh command must be one line, got: {lines!r}"
    return lines[0]


def test_remote_setup_dry_run_prints_connection_command() -> None:
    fake = make_fake_context(runner=_runner_with_status(), interactive=True)
    result = runner.invoke(app, ["remote", "setup", "--dry-run"], obj=fake, env={"COLUMNS": "40"})
    assert result.exit_code == 0
    line = _mosh_line(result.output)
    assert "zellij attach --create mobile" in line


def test_remote_setup_session_flag_changes_command() -> None:
    fake = make_fake_context(runner=_runner_with_status(), interactive=True)
    result = runner.invoke(
        app, ["remote", "setup", "--dry-run", "--session", "work"], obj=fake, env={"COLUMNS": "40"}
    )
    assert result.exit_code == 0
    line = _mosh_line(result.output)
    assert "zellij attach --create work" in line


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
