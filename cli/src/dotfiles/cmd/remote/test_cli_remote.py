from pathlib import Path

from typer.testing import CliRunner

from dotfiles.app.main import app
from dotfiles.testing.fakes import FakeProcessRunner, make_fake_context

runner = CliRunner()


def _runner_with_status(remote_login: str = "Off") -> FakeProcessRunner:
    r = FakeProcessRunner()
    r.script(("id", "-un"), stdout="evan\n")
    r.script(("scutil", "--get", "LocalHostName"), stdout="Evans-MBP-M4\n")
    sshd = "enabled" if remote_login == "On" else "disabled"
    r.script(
        ("launchctl", "print-disabled", "system"),
        stdout=f'\t"com.openssh.sshd" => {sshd}\n',
    )
    r.script(("tailscale", "status"), exit_code=1)
    r.script(("mosh", "--version"), stdout="mosh 1.4.0\n")
    r.script(("zellij", "--version"), stdout="zellij 0.44.3\n")
    return r


def _flat(output: str) -> str:
    """Collapse Rich's line-wrapping so multi-line assertions work (DRY-RUN step messages only)."""
    return " ".join(output.split())


def _mosh_line(output: str) -> str:
    """Return the direct-attach mosh command line (first mosh line in output).

    A second mosh line (picker variant, `-- dotfiles session`) follows the
    first; callers testing the direct-attach command still work because the
    `dotfiles session attach <name>` form only appears in the first line.
    """
    lines = [ln for ln in output.splitlines() if ln.startswith("mosh --server=")]
    assert len(lines) >= 1, f"expected at least one mosh line, got: {lines!r}"
    return lines[0]


def test_remote_web_status_prints_localhost_hint() -> None:
    r = FakeProcessRunner()
    r.script(("zellij", "web", "--status"), exit_code=1)
    result = runner.invoke(app, ["remote", "web"], obj=make_fake_context(runner=r))
    assert result.exit_code == 0
    assert "127.0.0.1:8082" in _flat(result.output)


def test_remote_web_start_invokes_daemon() -> None:
    r = FakeProcessRunner()
    result = runner.invoke(app, ["remote", "web", "--start"], obj=make_fake_context(runner=r))
    assert result.exit_code == 0
    assert ("zellij", "web", "-d") in r.calls


def test_remote_setup_dry_run_prints_connection_command() -> None:
    fake = make_fake_context(runner=_runner_with_status(), interactive=True)
    result = runner.invoke(app, ["remote", "on", "--dry-run"], obj=fake, env={"COLUMNS": "40"})
    assert result.exit_code == 0
    line = _mosh_line(result.output)
    assert "dotfiles session attach mobile" in line


def test_remote_setup_session_flag_changes_command() -> None:
    fake = make_fake_context(runner=_runner_with_status(), interactive=True)
    result = runner.invoke(
        app, ["remote", "on", "--dry-run", "--session", "work"], obj=fake, env={"COLUMNS": "40"}
    )
    assert result.exit_code == 0
    line = _mosh_line(result.output)
    assert "dotfiles session attach work" in line


def test_remote_setup_bad_key_exits_nonzero(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    fake = make_fake_context(runner=_runner_with_status(), interactive=True, home=home)
    result = runner.invoke(app, ["remote", "on", "--add-key", "garbage"], obj=fake)
    assert result.exit_code != 0
    assert "does not look like" in result.output.lower() or "invalid" in result.output.lower()


def test_remote_setup_warns_when_tailscale_disconnected() -> None:
    fake = make_fake_context(runner=_runner_with_status(), interactive=True)
    result = runner.invoke(app, ["remote", "on", "--dry-run"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "Tailscale not connected" in result.output


def test_remote_on_tailscale_flag_brings_tailnet_up() -> None:
    fake = make_fake_context(runner=_runner_with_status(), interactive=True)
    result = runner.invoke(
        app, ["remote", "on", "--dry-run", "--tailscale"], obj=fake, env={"COLUMNS": "200"}
    )
    assert result.exit_code == 0
    assert "DRY RUN: tailscale up" in _flat(result.output)


def test_remote_off_nudges_to_sharing_pane_when_on() -> None:
    r = _runner_with_status("On")
    fake = make_fake_context(runner=r, interactive=False)
    result = runner.invoke(app, ["remote", "off"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 0  # nudges, never errors — it doesn't flip the toggle
    assert "Remote Login is ON" in result.output
    assert "Sharing" in result.output
    # `off` now opens the exact pane too (it didn't before).
    assert any(c[0] == "open" and "Sharing" in c[1] for c in r.calls)


def test_remote_off_already_disabled_says_so() -> None:
    fake = make_fake_context(runner=_runner_with_status("Off"), interactive=True)
    result = runner.invoke(app, ["remote", "off"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "already disabled" in result.output


def test_remote_off_tailscale_flag_brings_tailnet_down() -> None:
    r = _runner_with_status("On")
    fake = make_fake_context(runner=r, interactive=False)
    result = runner.invoke(app, ["remote", "off", "--tailscale"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert ("tailscale", "down") in r.calls


def test_remote_off_kill_sessions_dry_run() -> None:
    fake = make_fake_context(runner=_runner_with_status("On"), interactive=True)
    result = runner.invoke(app, ["remote", "off", "--dry-run", "--kill-sessions"], obj=fake)
    assert result.exit_code == 0
    assert "DRY RUN" in result.output


def test_remote_status_shows_fields() -> None:
    fake = make_fake_context(runner=_runner_with_status("On"), interactive=True)
    result = runner.invoke(app, ["remote", "status"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "Remote Login" in result.output
    assert "Tailscale" in result.output
    # Settings/Shortcut nest beneath Remote Login as owned tree-branch children.
    assert "└─ Shortcut" in result.output
    assert "Sharing" in result.output  # in the nested Settings path


def test_remote_status_off_has_no_ssh_auth_child() -> None:
    fake = make_fake_context(runner=_runner_with_status("Off"), interactive=True)
    result = runner.invoke(app, ["remote", "status"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "├─ Settings" in result.output  # Settings is the first child when off
    assert "SSH auth" not in result.output  # only shown when Remote Login is on
