from pathlib import Path

from dotfiles.cmd.remote.service import RemoteService, is_ssh_public_key
from dotfiles.testing.fakes import FakeProcessRunner


def _service(runner: FakeProcessRunner, home: Path, *, interactive: bool = False) -> RemoteService:
    return RemoteService(runner=runner, interactive=interactive, home=home)


def test_web_start_reports_success(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    step = _service(runner, tmp_path).web_start()
    assert ("zellij", "web", "-d") in runner.calls
    assert step.level == "success"


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


def test_accepts_ed25519_rsa_ecdsa() -> None:
    assert is_ssh_public_key("ssh-ed25519 AAAAC3Nza... phone")
    assert is_ssh_public_key("ssh-rsa AAAAB3Nza... phone")
    assert is_ssh_public_key("ecdsa-sha2-nistp256 AAAA... phone")


def test_rejects_garbage_and_private_keys() -> None:
    assert not is_ssh_public_key("hello world")
    assert not is_ssh_public_key("-----BEGIN OPENSSH PRIVATE KEY-----")
    assert not is_ssh_public_key("")
    assert not is_ssh_public_key("ssh-ed25519")  # no key body


def test_status_reads_system_state(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("launchctl", "print-disabled", "system"), stdout='\t"com.openssh.sshd" => enabled\n'
    )
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("scutil", "--get", "LocalHostName"), stdout="Evans-MBP-M4\n")
    runner.script(("tailscale", "status"), exit_code=0)
    runner.script(("tailscale", "ip", "-4"), stdout="100.64.0.10\n")

    status = _service(runner, tmp_path).status()

    assert status.remote_login_on is True
    assert status.user == "evan"
    assert status.host == "Evans-MBP-M4"
    assert status.tailscale_connected is True
    assert status.tailnet_ip == "100.64.0.10"


def test_status_handles_remote_login_off_and_no_tailscale(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("launchctl", "print-disabled", "system"), stdout='\t"com.openssh.sshd" => disabled\n'
    )
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("scutil", "--get", "LocalHostName"), stdout="Evans-MBP-M4\n")
    runner.script(("tailscale", "status"), exit_code=1)

    status = _service(runner, tmp_path).status()

    assert status.remote_login_on is False
    assert status.tailscale_connected is False
    assert status.tailnet_ip is None


def test_status_reports_ssh_key_only_when_password_and_kbd_off(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("launchctl", "print-disabled", "system"), stdout='\t"com.openssh.sshd" => enabled\n'
    )
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("tailscale", "status"), exit_code=1)
    runner.script(
        ("/usr/sbin/sshd", "-G"),
        stdout="passwordauthentication no\nkbdinteractiveauthentication no\n",
    )

    assert _service(runner, tmp_path).status().ssh_password_auth is False


def test_status_reports_password_allowed_when_either_method_on(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("launchctl", "print-disabled", "system"), stdout='\t"com.openssh.sshd" => enabled\n'
    )
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("tailscale", "status"), exit_code=1)
    runner.script(
        ("/usr/sbin/sshd", "-G"),
        stdout="passwordauthentication no\nkbdinteractiveauthentication yes\n",
    )

    assert _service(runner, tmp_path).status().ssh_password_auth is True


def test_status_ssh_auth_unknown_when_sshd_query_fails(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("launchctl", "print-disabled", "system"), stdout='\t"com.openssh.sshd" => enabled\n'
    )
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("tailscale", "status"), exit_code=1)
    runner.script(("/usr/sbin/sshd", "-G"), exit_code=1)

    assert _service(runner, tmp_path).status().ssh_password_auth is None


def test_sudo_failure_surfaces_underlying_stderr(tmp_path: Path) -> None:
    runner = _base_runner()  # scripts `sudo -n true` ok so _sudo runs the real call
    runner.script(
        ("sudo", "mkdir", "-p", "/etc/ssh/sshd_config.d"),
        exit_code=1,
        stderr="mkdir: /etc/ssh: Operation not permitted\n",
    )
    service = RemoteService(
        runner=runner,
        interactive=True,
        home=tmp_path,
        which=lambda _name: "/opt/homebrew/bin/mosh-server",
    )

    steps = service.setup(dry_run=False, add_key=None, harden=True, session="mobile")

    err = [s for s in steps if s.level == "error"]
    assert err, "expected an error step on sudo failure"
    assert "Operation not permitted" in err[0].message


def _base_runner() -> FakeProcessRunner:
    runner = FakeProcessRunner()
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("scutil", "--get", "LocalHostName"), stdout="Evans-MBP-M4\n")
    runner.script(
        ("launchctl", "print-disabled", "system"), stdout='\t"com.openssh.sshd" => disabled\n'
    )
    runner.script(("tailscale", "status"), exit_code=1)
    runner.script(("mosh", "--version"), stdout="mosh 1.4.0\n")
    runner.script(("zellij", "--version"), stdout="zellij 0.44.3\n")
    runner.script(("sudo", "-n", "true"), exit_code=0)
    return runner


def test_setup_dry_run_makes_no_mutating_calls(tmp_path: Path) -> None:
    runner = _base_runner()
    service = RemoteService(
        runner=runner,
        interactive=False,
        home=tmp_path,
        which=lambda _name: "/opt/homebrew/bin/mosh-server",
    )

    steps = service.setup(dry_run=True, add_key=None, harden=False, session="mobile")

    # No sudo systemsetup mutation, no authorized_keys written.
    assert ("sudo", "systemsetup", "-setremotelogin", "on") not in runner.calls
    assert not (tmp_path / ".ssh" / "authorized_keys").exists()
    assert any("DRY RUN" in s.message for s in steps)


def test_setup_adds_key_idempotently_and_nudges_remote_login(tmp_path: Path) -> None:
    runner = _base_runner()  # _base_runner reports Remote Login disabled
    service = RemoteService(
        runner=runner,
        interactive=True,
        home=tmp_path,
        which=lambda _name: "/opt/homebrew/bin/mosh-server",
    )
    key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITEST phone"

    service.setup(dry_run=False, add_key=key, harden=False, session="mobile")
    # second run must not duplicate the key
    steps = service.setup(dry_run=False, add_key=key, harden=False, session="mobile")

    contents = (tmp_path / ".ssh" / "authorized_keys").read_text()
    assert contents.count(key) == 1
    # The CLI never flips Remote Login itself — it nudges to the Sharing toggle.
    assert ("sudo", "systemsetup", "-setremotelogin", "on") not in runner.calls
    assert any(s.level == "warn" and "Remote Login is off" in s.message for s in steps)


def test_setup_reports_existing_authorized_key_without_flag(tmp_path: Path) -> None:
    # A key added on a prior run is reported as present, not nagged about.
    keys = tmp_path / ".ssh" / "authorized_keys"
    keys.parent.mkdir(parents=True)
    keys.write_text("ssh-ed25519 AAAAC3NzaPHONE phone\n")
    service = RemoteService(
        runner=_base_runner(), interactive=True, home=tmp_path, which=lambda _n: "/x"
    )
    steps = service.setup(dry_run=False, add_key=None, harden=False, session="mobile")
    assert any(s.level == "success" and "already authorized" in s.message for s in steps)
    assert not any("No phone key" in s.message for s in steps)


def test_setup_reports_key_only_when_already_hardened(tmp_path: Path) -> None:
    # With no --harden-ssh flag, report the EFFECTIVE state, not "rerun the flag".
    runner = _base_runner()
    runner.script(
        ("/usr/sbin/sshd", "-G"),
        stdout="passwordauthentication no\nkbdinteractiveauthentication no\n",
    )
    service = RemoteService(runner=runner, interactive=True, home=tmp_path, which=lambda _n: "/x")
    steps = service.setup(dry_run=False, add_key=None, harden=False, session="mobile")
    assert any(s.level == "success" and "key-only" in s.message for s in steps)


def test_setup_opens_sharing_settings_when_remote_login_off(tmp_path: Path) -> None:
    runner = _base_runner()  # reports Remote Login disabled
    service = RemoteService(runner=runner, interactive=True, home=tmp_path, which=lambda _n: "/x")
    service.setup(dry_run=False, add_key=None, harden=False, session="mobile")
    assert any(c[0] == "open" and "Sharing" in c[1] for c in runner.calls)


def test_setup_rejects_bad_key(tmp_path: Path) -> None:
    import pytest

    from dotfiles.cmd.remote.service import InvalidKeyError

    service = RemoteService(runner=_base_runner(), interactive=True, home=tmp_path)
    with pytest.raises(InvalidKeyError):
        service.setup(dry_run=False, add_key="not a key", harden=False, session="mobile")
    # Fail-fast: a malformed key must raise before any filesystem mutation.
    assert not (tmp_path / ".ssh").exists()


def test_setup_without_sudo_access_warns_instead_of_running(tmp_path: Path) -> None:
    runner = _base_runner()
    runner.script(("sudo", "-n", "true"), exit_code=1)  # cannot sudo non-interactively
    service = RemoteService(
        runner=runner,
        interactive=False,
        home=tmp_path,
        which=lambda _name: "/opt/homebrew/bin/mosh-server",
    )

    # harden=True is the only step that still needs sudo (writes the key-only config).
    steps = service.setup(dry_run=False, add_key=None, harden=True, session="mobile")

    assert ("sudo", "systemsetup", "-setremotelogin", "on") not in runner.calls
    assert any("Needs sudo" in s.message for s in steps)


def test_disable_when_already_off_optionally_kills_sessions(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("launchctl", "print-disabled", "system"), stdout='\t"com.openssh.sshd" => disabled\n'
    )
    runner.script(("id", "-un"), stdout="evan\n")
    service = RemoteService(runner=runner, interactive=True, home=tmp_path)

    steps = service.disable(dry_run=False, kill_sessions=True)

    assert any("already disabled" in s.message for s in steps)
    assert ("pkill", "-u", "evan", "mosh-server") in runner.calls
    assert ("pkill", "-u", "evan", "sshd") in runner.calls


def test_disable_nudges_to_sharing_pane_when_on(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("launchctl", "print-disabled", "system"), stdout='\t"com.openssh.sshd" => enabled\n'
    )
    runner.script(("id", "-un"), stdout="evan\n")
    service = RemoteService(runner=runner, interactive=True, home=tmp_path)

    steps = service.disable(dry_run=False, kill_sessions=False)

    # Never flips it itself — surfaces the manual toggle instead.
    assert ("sudo", "systemsetup", "-setremotelogin", "-f", "off") not in runner.calls
    assert any(s.level == "warn" and "Remote Login is on" in s.message for s in steps)


def test_disable_dry_run_makes_no_changes(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("launchctl", "print-disabled", "system"), stdout='\t"com.openssh.sshd" => enabled\n'
    )
    runner.script(("id", "-un"), stdout="evan\n")
    service = RemoteService(runner=runner, interactive=True, home=tmp_path)

    steps = service.disable(dry_run=True, kill_sessions=True)

    assert ("sudo", "systemsetup", "-setremotelogin", "-f", "off") not in runner.calls
    assert ("pkill", "-u", "evan", "mosh-server") not in runner.calls
    assert any("DRY RUN" in s.message for s in steps)


def test_ensure_tool_reports_brew_install_failure(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("mosh", "--version"), exit_code=1)
    runner.script(("brew", "install", "mosh"), exit_code=1)
    runner.script(("zellij", "--version"), stdout="zellij 0.44.3\n")
    runner.script(
        ("launchctl", "print-disabled", "system"), stdout='\t"com.openssh.sshd" => enabled\n'
    )
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("sudo", "-n", "true"), exit_code=0)
    service = RemoteService(
        runner=runner,
        interactive=True,
        home=tmp_path,
        which=lambda _name: "/opt/homebrew/bin/mosh-server",
    )

    steps = service.setup(dry_run=False, add_key=None, harden=False, session="mobile")

    err = [s for s in steps if s.level == "error"]
    assert err, "expected an error step on brew install failure"
    assert "mosh" in err[0].message


def test_add_key_preserves_existing_key_without_trailing_newline(tmp_path: Path) -> None:
    keys = tmp_path / ".ssh" / "authorized_keys"
    keys.parent.mkdir(parents=True)
    keys.write_text("ssh-rsa AAAAOLD oldkey")  # no trailing newline
    runner = _base_runner()
    service = RemoteService(
        runner=runner,
        interactive=True,
        home=tmp_path,
        which=lambda _name: "/opt/homebrew/bin/mosh-server",
    )
    new = "ssh-ed25519 AAAANEW newkey"
    service.setup(dry_run=False, add_key=new, harden=False, session="mobile")
    lines = keys.read_text().splitlines()
    assert "ssh-rsa AAAAOLD oldkey" in lines
    assert new in lines


def test_setup_hardens_ssh_dir_and_authorized_keys_perms(tmp_path: Path) -> None:
    runner = _base_runner()
    service = RemoteService(
        runner=runner,
        interactive=True,
        home=tmp_path,
        which=lambda _name: "/opt/homebrew/bin/mosh-server",
    )
    service.setup(dry_run=False, add_key=None, harden=False, session="mobile")
    ssh_dir = tmp_path / ".ssh"
    keys = ssh_dir / "authorized_keys"
    assert (ssh_dir.stat().st_mode & 0o777) == 0o700
    assert (keys.stat().st_mode & 0o777) == 0o600


def test_setup_dry_run_does_not_chmod(tmp_path: Path) -> None:
    runner = _base_runner()
    service = RemoteService(
        runner=runner,
        interactive=True,
        home=tmp_path,
        which=lambda _name: "/opt/homebrew/bin/mosh-server",
    )
    service.setup(dry_run=True, add_key=None, harden=False, session="mobile")
    assert not (tmp_path / ".ssh").exists()


def test_setup_harden_writes_config_and_restarts_sshd(tmp_path: Path) -> None:
    runner = _base_runner()
    service = RemoteService(
        runner=runner,
        interactive=True,
        home=tmp_path,
        which=lambda _name: "/opt/homebrew/bin/mosh-server",
    )
    service.setup(dry_run=False, add_key=None, harden=True, session="mobile")
    assert (tmp_path / ".dotfiles-sshd-remote.conf").exists()
    assert ("sudo", "mkdir", "-p", "/etc/ssh/sshd_config.d") in runner.calls
    assert (
        "sudo",
        "install",
        "-m",
        "644",
        str(tmp_path / ".dotfiles-sshd-remote.conf"),
        "/etc/ssh/sshd_config.d/90-dotfiles-remote.conf",
    ) in runner.calls
    assert ("sudo", "launchctl", "kickstart", "-k", "system/com.openssh.sshd") in runner.calls


def test_kill_sessions_runs_pkill_without_disabling_remote_login(tmp_path: Path) -> None:
    """kill_sessions() must pkill mosh-server/sshd and NOT touch systemsetup -setremotelogin."""
    runner = FakeProcessRunner()
    runner.script(("id", "-un"), stdout="evan\n")
    service = RemoteService(runner=runner, interactive=True, home=tmp_path)

    steps = service.kill_sessions(dry_run=False)

    assert ("pkill", "-u", "evan", "mosh-server") in runner.calls
    assert ("pkill", "-u", "evan", "sshd") in runner.calls
    assert ("sudo", "systemsetup", "-setremotelogin", "-f", "off") not in runner.calls
    assert any(s.level == "success" for s in steps)


def test_kill_sessions_dry_run_does_not_execute_pkill(tmp_path: Path) -> None:
    """kill_sessions(dry_run=True) must only emit DRY RUN messages, never call pkill."""
    runner = FakeProcessRunner()
    runner.script(("id", "-un"), stdout="evan\n")
    service = RemoteService(runner=runner, interactive=True, home=tmp_path)

    steps = service.kill_sessions(dry_run=True)

    assert ("pkill", "-u", "evan", "mosh-server") not in runner.calls
    assert ("pkill", "-u", "evan", "sshd") not in runner.calls
    assert all("DRY RUN" in s.message for s in steps)
