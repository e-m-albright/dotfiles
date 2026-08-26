import plistlib
from pathlib import Path

from dotfiles.cmd.remote.service import RemoteService
from dotfiles.testing.fakes import FakeProcessRunner


def _service(runner: FakeProcessRunner, home: Path, *, interactive: bool = False) -> RemoteService:
    return RemoteService(runner=runner, interactive=interactive, home=home)


# --- Tailscale ------------------------------------------------------------


def test_tailscale_up_down_report_state(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    service = _service(runner, tmp_path)
    assert service.tailscale_up(dry_run=False).level == "success"
    assert ("tailscale", "up") in runner.calls
    assert service.tailscale_down(dry_run=False).level == "success"
    assert ("tailscale", "down") in runner.calls


def test_tailscale_up_surfaces_failure(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("tailscale", "up"), exit_code=1, stderr="needs login\n")
    step = _service(runner, tmp_path).tailscale_up(dry_run=False)
    assert step.level == "error"
    assert "needs login" in step.message


def test_tailscale_dry_run_makes_no_calls(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    assert "DRY RUN" in _service(runner, tmp_path).tailscale_down(dry_run=True).message
    assert ("tailscale", "down") not in runner.calls


# --- serve ----------------------------------------------------------------


def test_serve_start_exposes_zellij_web(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    step = _service(runner, tmp_path).serve_start(dry_run=False)
    assert step.level == "success"
    assert ("tailscale", "serve", "--bg", "8082") in runner.calls


def test_serve_reset_stops_exposure(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    step = _service(runner, tmp_path).serve_reset(dry_run=False)
    assert step.level == "success"
    assert ("tailscale", "serve", "reset") in runner.calls


def test_serve_dry_run_makes_no_calls(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    assert "DRY RUN" in _service(runner, tmp_path).serve_start(dry_run=True).message
    assert not any(c[:2] == ("tailscale", "serve") for c in runner.calls)


# --- Zellij web launchd agent ---------------------------------------------


def test_install_agent_writes_runtime_plist_and_bootstraps(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("id", "-u"), stdout="501\n")
    steps = _service(runner, tmp_path).install_agent(dry_run=False)

    plist = tmp_path / "Library" / "LaunchAgents" / "com.dotfiles.zellij-web.plist"
    assert plist.exists()
    content = plist.read_text()
    assert "com.dotfiles.zellij-web" in content
    assert "/opt/homebrew/bin/zellij" in content
    # Plist is rendered from home at runtime, so the log path is under this home.
    assert str(tmp_path) in content
    assert ("launchctl", "bootstrap", "gui/501", str(plist)) in runner.calls
    assert all(s.level != "error" for s in steps)


def test_install_agent_dry_run_writes_nothing(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    steps = _service(runner, tmp_path).install_agent(dry_run=True)
    assert not (tmp_path / "Library" / "LaunchAgents").exists()
    assert all("DRY RUN" in s.message for s in steps)
    assert not any(c[0] == "launchctl" for c in runner.calls)


def test_uninstall_agent_boots_out_and_removes_plist(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("id", "-u"), stdout="501\n")
    service = _service(runner, tmp_path)
    service.install_agent(dry_run=False)
    steps = service.uninstall_agent(dry_run=False)
    assert not (tmp_path / "Library" / "LaunchAgents" / "com.dotfiles.zellij-web.plist").exists()
    assert ("launchctl", "bootout", "gui/501/com.dotfiles.zellij-web") in runner.calls
    assert all(s.level == "success" for s in steps)


def test_zellij_web_running_reads_status(tmp_path: Path) -> None:
    up = FakeProcessRunner()
    up.script(("zellij", "web", "--status"), exit_code=0)
    assert _service(up, tmp_path).zellij_web_running() is True

    down = FakeProcessRunner()
    down.script(("zellij", "web", "--status"), exit_code=1)
    assert _service(down, tmp_path).zellij_web_running() is False


# --- Paseo daemon launchd agent -------------------------------------------


def test_paseo_install_agent_writes_plist_and_bootstraps(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("id", "-u"), stdout="501\n")
    runner.script(("tailscale", "status"), exit_code=0)
    runner.script(("tailscale", "ip", "-4"), stdout="100.64.0.1\n")
    steps = _service(runner, tmp_path).paseo_install_agent(dry_run=False)

    plist = tmp_path / "Library" / "LaunchAgents" / "com.dotfiles.paseo.plist"
    assert plist.exists()
    content = plistlib.loads(plist.read_bytes())
    assert content["Label"] == "com.dotfiles.paseo"
    assert content["RunAtLoad"] is True
    assert content["KeepAlive"] is False
    assert content["EnvironmentVariables"]["PATH"] == (
        f"{tmp_path}/.local/bin:{tmp_path}/.npm-global/bin:"
        "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    )
    assert content["ProgramArguments"] == [
        "/opt/homebrew/bin/fnm",
        "exec",
        "--using=default",
        "paseo",
        "start",
        "--foreground",
        "--no-relay",
        "--listen",
        "100.64.0.1:6767",
    ]
    assert (
        "/opt/homebrew/bin/fnm",
        "exec",
        "--using=default",
        "paseo",
        "daemon",
        "stop",
    ) in runner.calls
    assert ("launchctl", "bootstrap", "gui/501", str(plist)) in runner.calls
    assert all(s.level != "error" for s in steps)


def test_paseo_install_agent_requires_tailnet_ip(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("tailscale", "status"), exit_code=1)

    steps = _service(runner, tmp_path).paseo_install_agent(dry_run=False)

    assert [step.level for step in steps] == ["error"]
    assert "tailnet IPv4" in steps[0].message
    assert not (tmp_path / "Library" / "LaunchAgents" / "com.dotfiles.paseo.plist").exists()
    assert not any(call[0] == "launchctl" for call in runner.calls)


def test_paseo_uninstall_stops_legacy_daemon(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("id", "-u"), stdout="501\n")

    steps = _service(runner, tmp_path).paseo_uninstall_agent(dry_run=False)

    assert (
        "/opt/homebrew/bin/fnm",
        "exec",
        "--using=default",
        "paseo",
        "daemon",
        "stop",
    ) in runner.calls
    assert all(step.level == "success" for step in steps)


def test_paseo_rotate_password_uses_terminal_and_reloads_agent(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("id", "-u"), stdout="501\n")
    runner.script(("tailscale", "status"), exit_code=0)
    runner.script(("tailscale", "ip", "-4"), stdout="100.64.0.1\n")

    steps = _service(runner, tmp_path).paseo_rotate_password(dry_run=False)

    command = (
        "/opt/homebrew/bin/fnm",
        "exec",
        "--using=default",
        "paseo",
        "daemon",
        "set-password",
    )
    call_index = runner.calls.index(command)
    assert runner.capture_output[call_index] is False
    plist = tmp_path / "Library/LaunchAgents/com.dotfiles.paseo.plist"
    assert ("launchctl", "bootstrap", "gui/501", str(plist)) in runner.calls
    assert any("password updated" in step.message.lower() for step in steps)
    assert all(step.level != "error" for step in steps)


def test_paseo_rotate_password_does_not_restart_after_cancel(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("tailscale", "status"), exit_code=0)
    runner.script(("tailscale", "ip", "-4"), stdout="100.64.0.1\n")
    runner.script(
        (
            "/opt/homebrew/bin/fnm",
            "exec",
            "--using=default",
            "paseo",
            "daemon",
            "set-password",
        ),
        exit_code=1,
    )

    steps = _service(runner, tmp_path).paseo_rotate_password(dry_run=False)

    assert [step.level for step in steps] == ["error"]
    assert not any(call[0] == "launchctl" for call in runner.calls)


def test_paseo_running_reads_launchctl_list(tmp_path: Path) -> None:
    up = FakeProcessRunner()
    up.script(("launchctl", "list"), stdout="123\t0\tcom.dotfiles.paseo\n")
    assert _service(up, tmp_path).paseo_running() is True

    down = FakeProcessRunner()
    down.script(("launchctl", "list"), stdout="123\t0\tcom.other\n")
    assert _service(down, tmp_path).paseo_running() is False

    # Loaded label whose process exited (KeepAlive off): PID column is "-".
    crashed = FakeProcessRunner()
    crashed.script(("launchctl", "list"), stdout="-\t0\tcom.dotfiles.paseo\n")
    assert _service(crashed, tmp_path).paseo_running() is False


# --- status / connection --------------------------------------------------


def test_status_reports_web_state(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("scutil", "--get", "LocalHostName"), stdout="mac\n")
    runner.script(("tailscale", "status"), exit_code=0)
    runner.script(("tailscale", "ip", "-4"), stdout="100.64.0.1\n")
    runner.script(("zellij", "web", "--status"), exit_code=0)
    runner.script(("launchctl", "list"), stdout="123\t0\tcom.dotfiles.paseo\n")

    status = _service(runner, tmp_path).status()

    assert status.tailscale_connected is True
    assert status.tailnet_ip == "100.64.0.1"
    assert status.zellij_web_running is True
    assert status.paseo_running is True
    assert status.host == "mac"


def test_connection_info_uses_magic_dns(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("scutil", "--get", "LocalHostName"), stdout="mac\n")
    runner.script(("tailscale", "status"), exit_code=0)
    runner.script(("tailscale", "ip", "-4"), stdout="100.64.0.1\n")
    runner.script(
        ("tailscale", "status", "--json"),
        stdout='{"Self": {"DNSName": "mac.tailnet.ts.net."}}',
    )
    info = _service(runner, tmp_path).connection_info("mobile")
    assert info.magic_dns == "mac.tailnet.ts.net"
    assert info.phone_url == "https://mac.tailnet.ts.net/mobile"
    # The Paseo app connects to the tailnet IP:port directly (no relay/TLS).
    assert info.paseo_addr == "100.64.0.1:6767"


def test_connection_info_off_tailnet_has_no_magic_dns(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("scutil", "--get", "LocalHostName"), stdout="mac\n")
    runner.script(("tailscale", "status"), exit_code=1)
    info = _service(runner, tmp_path).connection_info("mobile")
    assert info.tailnet_ip is None
    assert info.magic_dns is None
    assert info.phone_url == "https://mac/mobile"
    assert info.paseo_addr == "mac:6767"


# --- Zellij web token helpers ---------------------------------------------


def test_web_status_running_vs_stopped(tmp_path: Path) -> None:
    running = FakeProcessRunner()
    running.script(("zellij", "web", "--status"), stdout="Server running on 127.0.0.1:8082\n")
    assert _service(running, tmp_path).web_status().level == "info"

    stopped = FakeProcessRunner()
    stopped.script(("zellij", "web", "--status"), exit_code=1)
    assert "not running" in _service(stopped, tmp_path).web_status().message


def test_web_token_returns_token_text(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("zellij", "web", "--create-token"), stdout="token_0: abc123\n")
    step = _service(runner, tmp_path).web_token()
    assert step.level == "success"
    assert "abc123" in step.message


def test_mobile_session_step_ready_when_present(tmp_path: Path) -> None:
    r = FakeProcessRunner()
    r.script(
        ("zellij", "list-sessions", "--no-formatting"),
        stdout="mobile [Created 2m ago]\nfoo [Created 1h ago]\n",
    )
    step = _service(r, tmp_path).mobile_session_step(dry_run=False)
    assert step.level == "success"
    assert "ready" in step.message


def test_mobile_session_step_guides_when_absent(tmp_path: Path) -> None:
    r = FakeProcessRunner()
    r.script(("zellij", "list-sessions", "--no-formatting"), stdout="foo [Created 1h ago]\n")
    step = _service(r, tmp_path).mobile_session_step(dry_run=False)
    assert step.level == "warn"
    assert "zellij --session mobile --layout mobile" in step.message
