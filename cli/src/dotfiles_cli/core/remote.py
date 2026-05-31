"""Remote-shell setup/disable logic. Pure decisions over the ProcessRunner/FileSystem ports."""

import shutil
from collections.abc import Callable
from pathlib import Path

from dotfiles_cli.core.models import ConnectionInfo, RemoteStatus
from dotfiles_cli.core.ports import FileSystem, ProcessRunner

_KEY_PREFIXES = ("ssh-ed25519 ", "ssh-rsa ", "ecdsa-sha2-")

_HARDEN_PATH = "/etc/ssh/sshd_config.d/90-dotfiles-remote.conf"
_HARDEN_DIR = "/etc/ssh/sshd_config.d"
_HARDEN_CONTENT = (
    "PubkeyAuthentication yes\nPasswordAuthentication no\nKbdInteractiveAuthentication no\n"
)


def is_ssh_public_key(value: str) -> bool:
    """True if value looks like an SSH public key line (prefix + a key body)."""
    if not value.startswith(_KEY_PREFIXES):
        return False
    parts = value.split()
    return len(parts) >= 2 and bool(parts[1])


class RemoteService:
    """Sets up / disables the phone remote-shell entrypoint via the system ports."""

    def __init__(
        self,
        *,
        runner: ProcessRunner,
        fs: FileSystem,
        interactive: bool,
        home: Path,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self._runner = runner
        self._fs = fs
        self._interactive = interactive
        self._home = home
        self._which = which

    def _line(self, command: tuple[str, ...]) -> str:
        result = self._runner.run(command)
        return result.stdout.strip() if result.ok else ""

    def _user(self) -> str:
        return self._line(("id", "-un")) or "user"

    def _host(self) -> str:
        host = self._line(("scutil", "--get", "LocalHostName"))
        return host or self._line(("hostname", "-s")) or "localhost"

    def _mosh_server(self) -> str:
        if self._fs.exists(Path("/opt/homebrew/bin/mosh-server")):
            return "/opt/homebrew/bin/mosh-server"
        return self._which("mosh-server") or "/opt/homebrew/bin/mosh-server"

    def _remote_login_on(self) -> bool:
        return "On" in self._line(("systemsetup", "-getremotelogin"))

    def _tailscale(self) -> tuple[bool, str | None]:
        if self._runner.run(("tailscale", "status")).ok:
            ip = self._line(("tailscale", "ip", "-4")).splitlines()
            return True, (ip[0] if ip else None)
        return False, None

    def status(self) -> RemoteStatus:
        connected, ip = self._tailscale()
        return RemoteStatus(
            remote_login_on=self._remote_login_on(),
            tailscale_connected=connected,
            tailnet_ip=ip,
            host=self._host(),
            user=self._user(),
            mosh_server=self._mosh_server(),
        )

    def connection_info(self, session: str) -> ConnectionInfo:
        connected, ip = self._tailscale()
        return ConnectionInfo(
            user=self._user(),
            host=self._host(),
            session=session,
            mosh_server=self._mosh_server(),
            tailnet_ip=ip if connected else None,
        )
