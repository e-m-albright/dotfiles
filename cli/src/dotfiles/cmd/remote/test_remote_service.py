import plistlib
from pathlib import Path

from dotfiles.cmd.remote.service import RemoteService
from dotfiles.testing.fakes import FakeProcessRunner


def _service(runner: FakeProcessRunner, home: Path) -> RemoteService:
    return RemoteService(runner=runner, home=home)


def _tailnet(runner: FakeProcessRunner, ip: str = "100.64.0.1") -> None:
    runner.script(("tailscale", "status"), exit_code=0)
    runner.script(("tailscale", "ip", "-4"), stdout=f"{ip}\n")


def test_tailscale_up_down_and_dry_run(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    service = _service(runner, tmp_path)
    assert service.tailscale_up(dry_run=False).level == "success"
    assert service.tailscale_down(dry_run=False).level == "success"
    before = list(runner.calls)
    assert "DRY RUN" in service.tailscale_down(dry_run=True).message
    assert runner.calls == before


def test_tailscale_failure_is_visible(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("tailscale", "up"), exit_code=1, stderr="needs login\n")
    assert "needs login" in _service(runner, tmp_path).tailscale_up(dry_run=False).message


def test_paseo_install_requires_tailnet_ip(tmp_path: Path) -> None:
    steps = _service(FakeProcessRunner(), tmp_path).paseo_install_agent(dry_run=False)
    assert [step.level for step in steps] == ["error"]
    assert not (tmp_path / "Library/LaunchAgents/com.dotfiles.paseo.plist").exists()


def test_paseo_install_writes_tailnet_bound_no_relay_plist(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("id", "-u"), stdout="501\n")
    _tailnet(runner)

    steps = _service(runner, tmp_path).paseo_install_agent(dry_run=False)

    plist = tmp_path / "Library/LaunchAgents/com.dotfiles.paseo.plist"
    content = plistlib.loads(plist.read_bytes())
    assert content["ProgramArguments"][-2:] == ["--listen", "100.64.0.1:6767"]
    assert "--no-relay" in content["ProgramArguments"]
    assert content["KeepAlive"] is False
    assert ("launchctl", "bootstrap", "gui/501", str(plist)) in runner.calls
    assert all(step.level != "error" for step in steps)


def test_paseo_install_dry_run_writes_nothing(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    steps = _service(runner, tmp_path).paseo_install_agent(dry_run=True)
    assert all("DRY RUN" in step.message for step in steps)
    assert not (tmp_path / "Library/LaunchAgents").exists()


def test_paseo_running_requires_live_launchd_pid(tmp_path: Path) -> None:
    running = FakeProcessRunner()
    running.script(("launchctl", "list"), stdout="123\t0\tcom.dotfiles.paseo\n")
    assert _service(running, tmp_path).paseo_running() is True

    crashed = FakeProcessRunner()
    crashed.script(("launchctl", "list"), stdout="-\t0\tcom.dotfiles.paseo\n")
    assert _service(crashed, tmp_path).paseo_running() is False


def test_paseo_uninstall_removes_plist_and_stops_daemon(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("id", "-u"), stdout="501\n")
    plist = tmp_path / "Library/LaunchAgents/com.dotfiles.paseo.plist"
    plist.parent.mkdir(parents=True)
    plist.write_text("stale")

    steps = _service(runner, tmp_path).paseo_uninstall_agent(dry_run=False)

    assert not plist.exists()
    assert ("launchctl", "bootout", "gui/501/com.dotfiles.paseo") in runner.calls
    assert any(call[-2:] == ("daemon", "stop") for call in runner.calls)
    assert all(step.level == "success" for step in steps)


def test_paseo_rotation_uses_hidden_prompt_and_reloads(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("id", "-u"), stdout="501\n")
    _tailnet(runner)

    steps = _service(runner, tmp_path).paseo_rotate_password(dry_run=False)

    command = (
        "/Applications/Paseo.app/Contents/Resources/bin/paseo",
        "daemon",
        "set-password",
    )
    index = runner.calls.index(command)
    assert runner.capture_output[index] is False
    assert any("password updated" in step.message.lower() for step in steps)


def test_ensure_paseo_reinstalls_stale_tailnet_binding(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("id", "-u"), stdout="501\n")
    runner.script(("launchctl", "list"), stdout="123\t0\tcom.dotfiles.paseo\n")
    _tailnet(runner, "100.64.0.2")
    plist = tmp_path / "Library/LaunchAgents/com.dotfiles.paseo.plist"
    plist.parent.mkdir(parents=True)
    plist.write_bytes(
        plistlib.dumps({"ProgramArguments": ["paseo", "--listen", "100.64.0.1:6767"]})
    )

    steps = _service(runner, tmp_path).ensure_paseo_agent(dry_run=False)

    assert steps[0].level == "warn"
    assert "stale tailnet IP" in steps[0].message


def test_caffeine_status_reports_effective_sleep_prevention(tmp_path: Path) -> None:
    active = FakeProcessRunner()
    active.script(
        ("pmset", "-g", "assertions"),
        stdout=(
            'pid 1038(Caffeine): UserIsActive named: "Caffeine is Active"\n'
            "  Timeout will fire in 597 secs Action=TimeoutActionRelease\n"
        ),
    )
    assert _service(active, tmp_path).caffeine_status().summary == "active · preventing sleep"


def test_caffeine_status_reports_inactive_or_unavailable(tmp_path: Path) -> None:
    unavailable = FakeProcessRunner()
    unavailable.script(("pmset", "-g", "assertions"), exit_code=1)
    assert _service(unavailable, tmp_path).caffeine_status().summary == "unavailable"

    inactive = FakeProcessRunner()
    inactive.script(("pmset", "-g", "assertions"), stdout="PreventSystemSleep 0\n")
    assert _service(inactive, tmp_path).caffeine_status().summary == "inactive"


def test_status_and_connection_report_only_paseo_path(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("id", "-un"), stdout="dev\n")
    runner.script(("scutil", "--get", "LocalHostName"), stdout="mac\n")
    runner.script(("launchctl", "list"), stdout="123\t0\tcom.dotfiles.paseo\n")
    _tailnet(runner)
    runner.script(
        ("pmset", "-g", "assertions"),
        stdout='pid 1038(Caffeine): PreventUserIdleSystemSleep named: "Caffeine is Active"\n',
    )
    service = _service(runner, tmp_path)

    status = service.status()
    assert status.paseo_running is True
    assert status.caffeine.summary == "active · preventing sleep"
    assert status.tailnet_ip == "100.64.0.1"
    assert service.connection_info().paseo_addr == "100.64.0.1:6767"


def test_disconnected_status_falls_back_to_hostname(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("tailscale", "status"), exit_code=1)
    runner.script(("hostname", "-s"), stdout="fallback\n")
    service = _service(runner, tmp_path)
    assert service.status().tailscale_connected is False
    assert service.connection_info().paseo_addr == "fallback:6767"


def test_bootstrap_failure_is_reported(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("id", "-u"), stdout="501\n")
    _tailnet(runner)
    plist = tmp_path / "Library/LaunchAgents/com.dotfiles.paseo.plist"
    runner.script(
        ("launchctl", "bootstrap", "gui/501", str(plist)),
        exit_code=1,
        stderr="bad plist",
    )
    steps = _service(runner, tmp_path).paseo_install_agent(dry_run=False)
    assert steps[-1].level == "error"
    assert "bad plist" in steps[-1].message


def test_rotation_cancel_missing_tailnet_and_dry_run(tmp_path: Path) -> None:
    missing = _service(FakeProcessRunner(), tmp_path).paseo_rotate_password(dry_run=False)
    assert missing[0].level == "error"

    dry = _service(FakeProcessRunner(), tmp_path).paseo_rotate_password(dry_run=True)
    assert len(dry) == 2
    assert all("DRY RUN" in step.message for step in dry)

    cancelled_runner = FakeProcessRunner()
    _tailnet(cancelled_runner)
    cancelled_runner.script(
        (
            "/Applications/Paseo.app/Contents/Resources/bin/paseo",
            "daemon",
            "set-password",
        ),
        exit_code=1,
    )
    cancelled = _service(cancelled_runner, tmp_path).paseo_rotate_password(dry_run=False)
    assert cancelled[0].level == "error"


def test_malformed_listen_plists_are_ignored(tmp_path: Path) -> None:
    service = _service(FakeProcessRunner(), tmp_path)
    plist = tmp_path / "Library/LaunchAgents/com.dotfiles.paseo.plist"
    plist.parent.mkdir(parents=True)
    for payload in (
        b"not a plist",
        plistlib.dumps({"ProgramArguments": "bad"}),
        plistlib.dumps({"ProgramArguments": ["paseo"]}),
        plistlib.dumps({"ProgramArguments": ["--listen"]}),
    ):
        plist.write_bytes(payload)
        assert service._paseo_listen_address() is None


def test_ensure_running_matching_daemon_is_left_alone(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("launchctl", "list"), stdout="123\t0\tcom.dotfiles.paseo\n")
    _tailnet(runner)
    plist = tmp_path / "Library/LaunchAgents/com.dotfiles.paseo.plist"
    plist.parent.mkdir(parents=True)
    plist.write_bytes(
        plistlib.dumps({"ProgramArguments": ["paseo", "--listen", "100.64.0.1:6767"]})
    )
    steps = _service(runner, tmp_path).ensure_paseo_agent(dry_run=False)
    assert [step.level for step in steps] == ["info"]


def test_tailscale_down_failure_is_visible(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("tailscale", "down"), exit_code=1, stderr="denied")
    step = _service(runner, tmp_path).tailscale_down(dry_run=False)
    assert step.level == "error"
    assert "denied" in step.message
