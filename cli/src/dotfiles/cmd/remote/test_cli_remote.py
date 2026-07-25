from pathlib import Path

from typer.testing import CliRunner

from dotfiles.app.main import app
from dotfiles.testing.fakes import FakeProcessRunner, make_fake_context

runner = CliRunner()


def _runner_with_status(*, tailscale_up: bool = False) -> FakeProcessRunner:
    r = FakeProcessRunner()
    r.script(("id", "-un"), stdout="evan\n")
    r.script(("scutil", "--get", "LocalHostName"), stdout="Evans-MBP-M4\n")
    r.script(("tailscale", "status"), exit_code=0 if tailscale_up else 1)
    if tailscale_up:
        r.script(("tailscale", "ip", "-4"), stdout="100.64.0.1\n")
    return r


def _flat(output: str) -> str:
    """Collapse Rich's line-wrapping so multi-line assertions work (DRY-RUN step messages only)."""
    return " ".join(output.split())


def test_remote_pi_creates_project_session(tmp_path: Path) -> None:
    project = tmp_path / "code" / "private" / "garden"
    project.mkdir(parents=True)
    r = FakeProcessRunner()
    r.script(("zellij", "list-sessions", "--no-formatting"), stdout="")
    fake = make_fake_context(runner=r, home=tmp_path)

    result = runner.invoke(app, ["remote", "pi", "garden"], obj=fake)

    assert result.exit_code == 0
    command = fake.launcher.attached[0]
    assert command[:3] == ["zellij", "--session", "pi-garden"]
    assert "pi --continue" in command[-1]
    assert str(project) in command[-1]


def test_remote_pi_attaches_existing_project_session(tmp_path: Path) -> None:
    project = tmp_path / "code" / "public" / "garden"
    project.mkdir(parents=True)
    r = FakeProcessRunner()
    r.script(
        ("zellij", "list-sessions", "--no-formatting"),
        stdout="pi-garden [Created 2m 3s ago]\n",
    )
    fake = make_fake_context(runner=r, home=tmp_path)

    result = runner.invoke(app, ["remote", "pi", "garden"], obj=fake)

    assert result.exit_code == 0
    assert fake.launcher.attached == [["zellij", "attach", "pi-garden"]]


def test_remote_pi_reports_missing_project(tmp_path: Path) -> None:
    fake = make_fake_context(home=tmp_path)

    result = runner.invoke(app, ["remote", "pi", "missing"], obj=fake)

    assert result.exit_code == 1
    assert "not found" in result.output


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


def test_remote_off_resets_serve() -> None:
    r = FakeProcessRunner()
    fake = make_fake_context(runner=r, interactive=False)
    result = runner.invoke(app, ["remote", "off"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert ("tailscale", "serve", "reset") in r.calls


def test_remote_off_tailscale_flag_brings_tailnet_down() -> None:
    r = FakeProcessRunner()
    fake = make_fake_context(runner=r, interactive=False)
    result = runner.invoke(app, ["remote", "off", "--tailscale"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert ("tailscale", "down") in r.calls


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


def test_remote_qr_encodes_zellij_url(tmp_path: Path) -> None:
    r = _runner_with_status(tailscale_up=True)
    r.script(
        ("tailscale", "status", "--json"),
        stdout='{"Self": {"DNSName": "evans-mbp-m4.tailnet.ts.net."}}',
    )
    fake = make_fake_context(runner=r, home=tmp_path)
    result = runner.invoke(app, ["remote", "qr"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "evans-mbp-m4.tailnet.ts.net" in result.output


def test_remote_qr_warns_off_tailnet(tmp_path: Path) -> None:
    fake = make_fake_context(runner=_runner_with_status(), home=tmp_path)
    result = runner.invoke(app, ["remote", "qr"], obj=fake, env={"COLUMNS": "200"})
    assert result.exit_code == 1
    assert "Tailscale not connected" in result.output
