from pathlib import Path

import pytest
from typer.testing import CliRunner

from dotfiles.app.main import app
from dotfiles.testing.fakes import FakeProcessRunner, make_fake_context

runner = CliRunner()


def _tailnet(process: FakeProcessRunner, ip: str = "100.64.0.1") -> None:
    process.script(("tailscale", "status"), exit_code=0)
    process.script(("tailscale", "ip", "-4"), stdout=f"{ip}\n")


def test_remote_help_exposes_only_paseo_tailscale_and_status() -> None:
    result = runner.invoke(app, ["remote", "--help"])
    assert result.exit_code == 0
    for command in ("on", "off", "paseo", "tailscale", "status"):
        assert command in result.output
    assert "zellij" not in result.output.lower()


def test_remote_on_ensures_tailscale_and_paseo(tmp_path: Path) -> None:
    process = FakeProcessRunner()
    process.script(("id", "-u"), stdout="501\n")
    process.script(("scutil", "--get", "LocalHostName"), stdout="mac\n")
    _tailnet(process)
    process.script(
        ("pmset", "-g", "assertions"),
        stdout='pid 1038(Caffeine): PreventUserIdleSystemSleep named: "Caffeine is Active"\n',
    )

    result = runner.invoke(
        app,
        ["remote", "on"],
        obj=make_fake_context(runner=process, home=tmp_path),
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert ("tailscale", "up") in process.calls
    assert "com.dotfiles.paseo" in result.output
    assert "100.64.0.1:6767" in result.output
    assert "Caffeine" in result.output
    assert "active · preventing sleep" in result.output
    assert (
        "tailscale",
        "serve",
        "--https=8443",
        "--bg",
        "--yes",
        "http://127.0.0.1:8765",
    ) in process.calls
    assert "Private site" in result.output


def test_remote_on_dry_run_has_no_effects(tmp_path: Path) -> None:
    process = FakeProcessRunner()
    result = runner.invoke(
        app,
        ["remote", "on", "--dry-run"],
        obj=make_fake_context(runner=process, home=tmp_path),
    )
    assert result.exit_code == 0
    assert "DRY RUN" in result.output
    assert ("tailscale", "up") not in process.calls
    assert not any(
        call[:2] in {("launchctl", "bootstrap"), ("launchctl", "bootout")} for call in process.calls
    )


def test_remote_off_only_disconnects_tailscale() -> None:
    process = FakeProcessRunner()
    result = runner.invoke(app, ["remote", "off"], obj=make_fake_context(runner=process))
    assert result.exit_code == 0
    assert process.calls == [("tailscale", "down")]
    assert "active agents keep running" in result.output


def test_remote_status_reports_direct_paseo_address() -> None:
    process = FakeProcessRunner()
    process.script(("id", "-un"), stdout="dev\n")
    process.script(("scutil", "--get", "LocalHostName"), stdout="mac\n")
    process.script(("launchctl", "list"), stdout="123\t0\tcom.dotfiles.paseo\n")
    _tailnet(process)
    process.script(
        ("pmset", "-g", "assertions"),
        stdout='pid 1038(Caffeine): PreventUserIdleSystemSleep named: "Caffeine is Active"\n',
    )

    result = runner.invoke(
        app,
        ["remote", "status"],
        obj=make_fake_context(runner=process),
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "Paseo" in result.output
    assert "100.64.0.1:6767" in result.output
    assert "active · preventing sleep" in result.output
    assert "Private site" in result.output
    assert "not configured" in result.output
    assert "Zellij" not in result.output


def test_remote_paseo_rejects_conflicting_actions() -> None:
    result = runner.invoke(
        app,
        ["remote", "paseo", "--start", "--stop"],
        obj=make_fake_context(),
    )
    assert result.exit_code != 0
    assert "Choose only one" in result.output


def test_remote_paseo_rotation_warns_before_restart(tmp_path: Path) -> None:
    process = FakeProcessRunner()
    process.script(("id", "-u"), stdout="501\n")
    _tailnet(process)
    result = runner.invoke(
        app,
        ["remote", "paseo", "--rotate-password"],
        obj=make_fake_context(runner=process, home=tmp_path),
        env={"COLUMNS": "200"},
    )
    assert result.exit_code == 0
    assert "interrupt active Paseo runs" in result.output


@pytest.mark.parametrize("args", [["--up", "--down"]])
def test_remote_tailscale_rejects_conflicting_actions(args: list[str]) -> None:
    result = runner.invoke(app, ["remote", "tailscale", *args], obj=make_fake_context())
    assert result.exit_code != 0


def test_remote_tailscale_status_up_and_down() -> None:
    process = FakeProcessRunner()
    _tailnet(process)
    status = runner.invoke(app, ["remote", "tailscale"], obj=make_fake_context(runner=process))
    up = runner.invoke(app, ["remote", "tailscale", "--up"], obj=make_fake_context())
    down = runner.invoke(app, ["remote", "tailscale", "--down"], obj=make_fake_context())
    assert status.exit_code == up.exit_code == down.exit_code == 0
    assert "100.64.0.1" in status.output


def test_remote_tailscale_failure_exits_nonzero() -> None:
    process = FakeProcessRunner()
    process.script(("tailscale", "up"), exit_code=1, stderr="denied")
    result = runner.invoke(
        app,
        ["remote", "tailscale", "--up"],
        obj=make_fake_context(runner=process),
    )
    assert result.exit_code == 1


def test_remote_paseo_status_start_failure_and_stop_dry_run(tmp_path: Path) -> None:
    status = runner.invoke(app, ["remote", "paseo"], obj=make_fake_context())
    missing = runner.invoke(
        app,
        ["remote", "paseo", "--start"],
        obj=make_fake_context(home=tmp_path),
    )
    stopped = runner.invoke(
        app,
        ["remote", "paseo", "--stop", "--dry-run"],
        obj=make_fake_context(home=tmp_path),
    )
    assert status.exit_code == 0
    assert "stopped" in status.output
    assert missing.exit_code == 1
    assert stopped.exit_code == 0
    assert "DRY RUN" in stopped.output


def test_remote_on_reports_failure_without_tailnet(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["remote", "on", "--no-tailscale"],
        obj=make_fake_context(home=tmp_path),
    )
    assert result.exit_code == 1
    assert "no tailnet IPv4" in result.output


def test_remote_off_failure_exits_nonzero() -> None:
    process = FakeProcessRunner()
    process.script(("tailscale", "down"), exit_code=1, stderr="denied")
    result = runner.invoke(app, ["remote", "off"], obj=make_fake_context(runner=process))
    assert result.exit_code == 1
