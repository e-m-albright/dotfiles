from pathlib import Path

from dotfiles_cli.core.remote import RemoteService, is_ssh_public_key
from tests.fakes import FakeFileSystem, FakeProcessRunner


def _service(runner: FakeProcessRunner, *, interactive: bool = False) -> RemoteService:
    return RemoteService(
        runner=runner, fs=FakeFileSystem(), interactive=interactive, home=Path("/home/evan")
    )


def test_accepts_ed25519_rsa_ecdsa() -> None:
    assert is_ssh_public_key("ssh-ed25519 AAAAC3Nza... phone")
    assert is_ssh_public_key("ssh-rsa AAAAB3Nza... phone")
    assert is_ssh_public_key("ecdsa-sha2-nistp256 AAAA... phone")


def test_rejects_garbage_and_private_keys() -> None:
    assert not is_ssh_public_key("hello world")
    assert not is_ssh_public_key("-----BEGIN OPENSSH PRIVATE KEY-----")
    assert not is_ssh_public_key("")
    assert not is_ssh_public_key("ssh-ed25519")  # no key body


def test_status_reads_system_state() -> None:
    runner = FakeProcessRunner()
    runner.script(("systemsetup", "-getremotelogin"), stdout="Remote Login: On\n")
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("scutil", "--get", "LocalHostName"), stdout="Evans-MBP-M4\n")
    runner.script(("tailscale", "status"), exit_code=0)
    runner.script(("tailscale", "ip", "-4"), stdout="100.64.0.10\n")

    status = _service(runner).status()

    assert status.remote_login_on is True
    assert status.user == "evan"
    assert status.host == "Evans-MBP-M4"
    assert status.tailscale_connected is True
    assert status.tailnet_ip == "100.64.0.10"


def test_status_handles_remote_login_off_and_no_tailscale() -> None:
    runner = FakeProcessRunner()
    runner.script(("systemsetup", "-getremotelogin"), stdout="Remote Login: Off\n")
    runner.script(("id", "-un"), stdout="evan\n")
    runner.script(("scutil", "--get", "LocalHostName"), stdout="Evans-MBP-M4\n")
    runner.script(("tailscale", "status"), exit_code=1)

    status = _service(runner).status()

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


def test_setup_dry_run_makes_no_mutating_calls() -> None:
    runner = _base_runner()
    fs = FakeFileSystem()
    service = RemoteService(
        runner=runner,
        fs=fs,
        interactive=False,
        home=Path("/home/evan"),
        which=lambda _name: "/opt/homebrew/bin/mosh-server",
    )

    steps = service.setup(dry_run=True, add_key=None, harden=False, session="mobile")

    # No sudo systemsetup mutation, no authorized_keys written.
    assert ("sudo", "systemsetup", "-setremotelogin", "on") not in runner.calls
    assert not fs.exists(Path("/home/evan/.ssh/authorized_keys"))
    assert any("DRY RUN" in s.message for s in steps)


def test_setup_adds_key_idempotently_and_enables_remote_login() -> None:
    runner = _base_runner()
    fs = FakeFileSystem()
    service = RemoteService(
        runner=runner,
        fs=fs,
        interactive=True,
        home=Path("/home/evan"),
        which=lambda _name: "/opt/homebrew/bin/mosh-server",
    )
    key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITEST phone"

    service.setup(dry_run=False, add_key=key, harden=False, session="mobile")
    # second run must not duplicate the key
    service.setup(dry_run=False, add_key=key, harden=False, session="mobile")

    contents = fs.read_text(Path("/home/evan/.ssh/authorized_keys"))
    assert contents.count(key) == 1
    assert ("sudo", "systemsetup", "-setremotelogin", "on") in runner.calls


def test_setup_rejects_bad_key() -> None:
    import pytest

    from dotfiles_cli.core.remote import InvalidKeyError

    service = RemoteService(
        runner=_base_runner(), fs=FakeFileSystem(), interactive=True, home=Path("/home/evan")
    )
    with pytest.raises(InvalidKeyError):
        service.setup(dry_run=False, add_key="not a key", harden=False, session="mobile")


def test_setup_without_sudo_access_warns_instead_of_running() -> None:
    runner = _base_runner()
    runner.script(("sudo", "-n", "true"), exit_code=1)  # cannot sudo non-interactively
    service = RemoteService(
        runner=runner,
        fs=FakeFileSystem(),
        interactive=False,
        home=Path("/home/evan"),
        which=lambda _name: "/opt/homebrew/bin/mosh-server",
    )

    steps = service.setup(dry_run=False, add_key=None, harden=False, session="mobile")

    assert ("sudo", "systemsetup", "-setremotelogin", "on") not in runner.calls
    assert any("Needs sudo" in s.message for s in steps)
