from pathlib import Path

from dotfiles.core.remote import RemoteService, is_ssh_public_key
from tests.fakes import FakeProcessRunner


def _service(runner: FakeProcessRunner, home: Path, *, interactive: bool = False) -> RemoteService:
    return RemoteService(runner=runner, interactive=interactive, home=home)


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
    runner.script(("systemsetup", "-getremotelogin"), stdout="Remote Login: On\n")
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
    runner.script(("systemsetup", "-getremotelogin"), stdout="Remote Login: Off\n")
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("scutil", "--get", "LocalHostName"), stdout="Evans-MBP-M4\n")
    runner.script(("tailscale", "status"), exit_code=1)

    status = _service(runner, tmp_path).status()

    assert status.remote_login_on is False
    assert status.tailscale_connected is False
    assert status.tailnet_ip is None


def _base_runner() -> FakeProcessRunner:
    runner = FakeProcessRunner()
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("scutil", "--get", "LocalHostName"), stdout="Evans-MBP-M4\n")
    runner.script(("systemsetup", "-getremotelogin"), stdout="Remote Login: Off\n")
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


def test_setup_adds_key_idempotently_and_enables_remote_login(tmp_path: Path) -> None:
    runner = _base_runner()
    service = RemoteService(
        runner=runner,
        interactive=True,
        home=tmp_path,
        which=lambda _name: "/opt/homebrew/bin/mosh-server",
    )
    key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITEST phone"

    service.setup(dry_run=False, add_key=key, harden=False, session="mobile")
    # second run must not duplicate the key
    service.setup(dry_run=False, add_key=key, harden=False, session="mobile")

    contents = (tmp_path / ".ssh" / "authorized_keys").read_text()
    assert contents.count(key) == 1
    assert ("sudo", "systemsetup", "-setremotelogin", "on") in runner.calls


def test_setup_rejects_bad_key(tmp_path: Path) -> None:
    import pytest

    from dotfiles.core.remote import InvalidKeyError

    service = RemoteService(runner=_base_runner(), interactive=True, home=tmp_path)
    with pytest.raises(InvalidKeyError):
        service.setup(dry_run=False, add_key="not a key", harden=False, session="mobile")


def test_setup_without_sudo_access_warns_instead_of_running(tmp_path: Path) -> None:
    runner = _base_runner()
    runner.script(("sudo", "-n", "true"), exit_code=1)  # cannot sudo non-interactively
    service = RemoteService(
        runner=runner,
        interactive=False,
        home=tmp_path,
        which=lambda _name: "/opt/homebrew/bin/mosh-server",
    )

    steps = service.setup(dry_run=False, add_key=None, harden=False, session="mobile")

    assert ("sudo", "systemsetup", "-setremotelogin", "on") not in runner.calls
    assert any("Needs sudo" in s.message for s in steps)


def test_disable_when_already_off_optionally_kills_sessions(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("systemsetup", "-getremotelogin"), stdout="Remote Login: Off\n")
    runner.script(("id", "-un"), stdout="evan\n")
    service = RemoteService(runner=runner, interactive=True, home=tmp_path)

    steps = service.disable(dry_run=False, kill_sessions=True)

    assert any("already disabled" in s.message for s in steps)
    assert ("pkill", "-u", "evan", "mosh-server") in runner.calls
    assert ("pkill", "-u", "evan", "sshd") in runner.calls


def test_disable_turns_off_remote_login_when_on(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("systemsetup", "-getremotelogin"), stdout="Remote Login: On\n")
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("sudo", "-n", "true"), exit_code=0)
    service = RemoteService(runner=runner, interactive=True, home=tmp_path)

    service.disable(dry_run=False, kill_sessions=False)

    assert ("sudo", "systemsetup", "-setremotelogin", "off") in runner.calls


def test_disable_dry_run_makes_no_changes(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("systemsetup", "-getremotelogin"), stdout="Remote Login: On\n")
    runner.script(("id", "-un"), stdout="evan\n")
    service = RemoteService(runner=runner, interactive=True, home=tmp_path)

    steps = service.disable(dry_run=True, kill_sessions=True)

    assert ("sudo", "systemsetup", "-setremotelogin", "off") not in runner.calls
    assert ("pkill", "-u", "evan", "mosh-server") not in runner.calls
    assert any("DRY RUN" in s.message for s in steps)


def test_sudo_failure_is_reported_as_error_with_fda_hint(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("systemsetup", "-getremotelogin"), stdout="Remote Login: On\n")
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("sudo", "systemsetup", "-setremotelogin", "off"), exit_code=1)
    service = RemoteService(runner=runner, interactive=True, home=tmp_path)

    steps = service.disable(dry_run=False, kill_sessions=False)

    err = [s for s in steps if s.level == "error"]
    assert err, "expected an error step on sudo failure"
    assert "Full Disk Access" in err[0].message


def test_ensure_tool_reports_brew_install_failure(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("mosh", "--version"), exit_code=1)
    runner.script(("brew", "install", "mosh"), exit_code=1)
    runner.script(("zellij", "--version"), stdout="zellij 0.44.3\n")
    runner.script(("systemsetup", "-getremotelogin"), stdout="Remote Login: On\n")
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
