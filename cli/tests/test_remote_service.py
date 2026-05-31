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
