from pathlib import Path

from typer.testing import CliRunner

from dotfiles.app.main import app
from dotfiles.testing.fakes import FakeProcessRunner, make_fake_context

runner = CliRunner()


def _runner_with_status(*, tailscale_up: bool = False) -> FakeProcessRunner:
    r = FakeProcessRunner()
    r.script(("id", "-un"), stdout="evan\n")
    r.script(("scutil", "--get", "LocalHostName"), stdout="test-mac-m4\n")
    r.script(("tailscale", "status"), exit_code=0 if tailscale_up else 1)
    if tailscale_up:
        r.script(("tailscale", "ip", "-4"), stdout="100.64.0.1\n")
    return r


def _flat(output: str) -> str:
    """Collapse Rich's line-wrapping so multi-line assertions work (DRY-RUN step messages only)."""
    return " ".join(output.split())


def test_remote_help_uses_service_names_and_removes_old_web_commands() -> None:
    help_result = runner.invoke(app, ["remote", "--help"])
    zellij_help = runner.invoke(app, ["remote", "zellij", "--help"])

    assert help_result.exit_code == zellij_help.exit_code == 0
    assert "tailscale" in help_result.output
    assert "zellij" in help_result.output
    assert "│ web " not in help_result.output
    assert "│ qr " not in help_result.output
    assert "qr" in zellij_help.output
    for removed in ("web", "qr"):
        result = runner.invoke(app, ["remote", removed])
        assert result.exit_code == 2


def test_remote_zellij_status_prints_localhost_hint() -> None:
    r = FakeProcessRunner()
    r.script(("zellij", "web", "--status"), exit_code=1)
    result = runner.invoke(app, ["remote", "zellij"], obj=make_fake_context(runner=r))
    assert result.exit_code == 0
    assert "127.0.0.1:8082" in _flat(result.output)


def test_remote_zellij_start_uses_launchd_and_exposes_tailnet(tmp_path: Path) -> None:
    r = _runner_with_status(tailscale_up=True)
    r.script(("id", "-u"), stdout="501\n")
    fake = make_fake_context(runner=r, home=tmp_path)

    result = runner.invoke(app, ["remote", "zellij", "--start"], obj=fake)

    assert result.exit_code == 0
    plist = tmp_path / "Library/LaunchAgents/com.dotfiles.zellij-web.plist"
    assert ("launchctl", "bootstrap", "gui/501", str(plist)) in r.calls
    assert ("tailscale", "serve", "--bg", "8082") in r.calls
    assert ("zellij", "web", "-d") not in r.calls


def test_remote_zellij_stop_removes_exposure_and_launchd_agent(tmp_path: Path) -> None:
    r = FakeProcessRunner()
    r.script(("id", "-u"), stdout="501\n")
    fake = make_fake_context(runner=r, home=tmp_path)

    result = runner.invoke(app, ["remote", "zellij", "--stop"], obj=fake)

    assert result.exit_code == 0
    assert ("tailscale", "serve", "reset") in r.calls
    assert ("launchctl", "bootout", "gui/501/com.dotfiles.zellij-web") in r.calls


def test_remote_on_dry_run_prints_fallback_url(tmp_path: Path) -> None:
    fake = make_fake_context(runner=_runner_with_status(), interactive=True, home=tmp_path)
    result = runner.invoke(app, ["remote", "on", "--dry-run"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 0
    # Connection info shows the Zellij web fallback, deep-linked to the session.
    assert "/mobile" in result.output
    assert "http://127.0.0.1:8082/mobile" in result.output


def test_remote_on_session_flag_changes_web_url(tmp_path: Path) -> None:
    fake = make_fake_context(runner=_runner_with_status(), interactive=True, home=tmp_path)
    result = runner.invoke(
        app, ["remote", "on", "--dry-run", "--session", "work"], obj=fake, env={"COLUMNS": "200"}
    )
    assert result.exit_code == 0
    assert "http://127.0.0.1:8082/work" in result.output


def test_remote_on_warns_when_tailscale_disconnected(tmp_path: Path) -> None:
    fake = make_fake_context(runner=_runner_with_status(), interactive=True, home=tmp_path)
    result = runner.invoke(app, ["remote", "on", "--dry-run"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "Tailscale not connected" in result.output


def test_remote_on_brings_tailnet_up_by_default(tmp_path: Path) -> None:
    fake = make_fake_context(runner=_runner_with_status(), interactive=True, home=tmp_path)
    result = runner.invoke(app, ["remote", "on", "--dry-run"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "DRY RUN: tailscale up" in _flat(result.output)


def test_remote_on_no_tailscale_skips_bringup(tmp_path: Path) -> None:
    fake = make_fake_context(runner=_runner_with_status(), interactive=True, home=tmp_path)
    result = runner.invoke(
        app, ["remote", "on", "--dry-run", "--no-tailscale"], obj=fake, env={"COLUMNS": "200"}
    )
    assert result.exit_code == 0
    assert "tailscale up" not in _flat(result.output).lower()


def test_remote_on_installs_paseo_agent(tmp_path: Path) -> None:
    fake = make_fake_context(runner=_runner_with_status(), interactive=True, home=tmp_path)
    result = runner.invoke(app, ["remote", "on", "--dry-run"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "com.dotfiles.paseo" in _flat(result.output)


def test_remote_on_does_not_reload_running_services(tmp_path: Path) -> None:
    r = _runner_with_status(tailscale_up=True)
    r.script(
        ("launchctl", "list"),
        stdout=("123\t0\tcom.dotfiles.paseo\n124\t0\tcom.dotfiles.zellij-web\n"),
    )
    r.script(("zellij", "web", "--status"), exit_code=0)
    fake = make_fake_context(runner=r, interactive=True, home=tmp_path)

    result = runner.invoke(app, ["remote", "on"], obj=fake, env={"COLUMNS": "200"})

    assert result.exit_code == 0
    assert not any(call[:2] == ("launchctl", "bootstrap") for call in r.calls)
    assert not any(call[-2:] == ("daemon", "stop") for call in r.calls)
    assert "already running" in _flat(result.output)


def test_remote_paseo_start_dry_run(tmp_path: Path) -> None:
    fake = make_fake_context(runner=_runner_with_status(), home=tmp_path)
    result = runner.invoke(
        app, ["remote", "paseo", "--start", "--dry-run"], obj=fake, env={"COLUMNS": "200"}
    )
    assert result.exit_code == 0
    assert "com.dotfiles.paseo" in _flat(result.output)


def test_remote_paseo_rotate_password_warns_restarts_and_prints_next_steps(
    tmp_path: Path,
) -> None:
    r = _runner_with_status(tailscale_up=True)
    r.script(("id", "-u"), stdout="501\n")
    fake = make_fake_context(runner=r, interactive=True, home=tmp_path)

    result = runner.invoke(
        app,
        ["remote", "paseo", "--rotate-password"],
        obj=fake,
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "interrupt active Paseo runs" in _flat(result.output)
    assert "100.64.0.1:6767" in result.output
    assert "desktop and mobile" in _flat(result.output)
    assert "password manager" in _flat(result.output)
    command = (
        "/opt/homebrew/bin/fnm",
        "exec",
        "--using=default",
        "paseo",
        "daemon",
        "set-password",
    )
    call_index = r.calls.index(command)
    assert r.capture_output[call_index] is False


def test_remote_off_breaks_connectivity_but_keeps_agents_running() -> None:
    r = FakeProcessRunner()
    fake = make_fake_context(runner=r, interactive=False)

    result = runner.invoke(app, ["remote", "off"], obj=fake, env={"COLUMNS": "200"})

    assert result.exit_code == 0
    assert ("tailscale", "serve", "reset") in r.calls
    assert ("tailscale", "down") in r.calls
    assert not any(call[:2] == ("zellij", "web") for call in r.calls)
    assert not any("paseo" in call for call in r.calls)
    assert "keep running" in _flat(result.output)


def test_remote_tailscale_manages_network_state() -> None:
    r = _runner_with_status(tailscale_up=True)
    fake = make_fake_context(runner=r, interactive=False)

    status = runner.invoke(app, ["remote", "tailscale"], obj=fake)
    down = runner.invoke(app, ["remote", "tailscale", "--down"], obj=fake)
    up = runner.invoke(app, ["remote", "tailscale", "--up"], obj=fake)

    assert status.exit_code == down.exit_code == up.exit_code == 0
    assert "connected" in status.output
    assert ("tailscale", "down") in r.calls
    assert ("tailscale", "up") in r.calls


def test_remote_status_shows_paseo_and_web_fields(tmp_path: Path) -> None:
    r = _runner_with_status(tailscale_up=True)
    r.script(
        ("tailscale", "status", "--json"),
        stdout='{"Self": {"DNSName": "evans-mbp-m4.tailnet.ts.net."}}',
    )
    fake = make_fake_context(runner=r, interactive=True, home=tmp_path)
    result = runner.invoke(app, ["remote", "status"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "Tailscale" in result.output
    assert "Paseo" in result.output
    assert "Zellij web" in result.output
    # The Paseo daemon address (tailnet IP:port) is shown.
    assert ":6767" in result.output


def test_remote_zellij_qr_encodes_zellij_url(tmp_path: Path) -> None:
    r = _runner_with_status(tailscale_up=True)
    r.script(
        ("tailscale", "status", "--json"),
        stdout='{"Self": {"DNSName": "evans-mbp-m4.tailnet.ts.net."}}',
    )
    fake = make_fake_context(runner=r, home=tmp_path)
    result = runner.invoke(app, ["remote", "zellij", "qr"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "evans-mbp-m4.tailnet.ts.net" in result.output


def test_remote_zellij_qr_warns_off_tailnet(tmp_path: Path) -> None:
    fake = make_fake_context(runner=_runner_with_status(), home=tmp_path)
    result = runner.invoke(app, ["remote", "zellij", "qr"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 1
    assert "Tailscale not connected" in result.output
