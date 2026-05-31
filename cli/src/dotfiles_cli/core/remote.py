"""Remote-shell setup/disable logic. Pure decisions over the ProcessRunner/FileSystem ports."""

import shutil
from collections.abc import Callable
from pathlib import Path

from dotfiles_cli.core.models import ConnectionInfo, RemoteStatus, StepResult
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


class InvalidKeyError(ValueError):
    """Raised when --add-key is not a valid SSH public key."""


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

    def _sudo(self, args: tuple[str, ...], *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(level="info", message="DRY RUN: sudo " + " ".join(args))
        if self._interactive or self._runner.run(("sudo", "-n", "true")).ok:
            self._runner.run(("sudo", *args))
            return StepResult(level="success", message="sudo " + " ".join(args))
        return StepResult(
            level="warn",
            message="Needs sudo in an interactive terminal. Run manually: sudo " + " ".join(args),
        )

    def _ensure_tool(self, name: str, *, dry_run: bool) -> StepResult:
        if self._runner.run((name, "--version")).ok:
            return StepResult(level="success", message=f"{name} available")
        if dry_run:
            return StepResult(level="info", message=f"DRY RUN: brew install {name}")
        self._runner.run(("brew", "install", name))
        return StepResult(level="success", message=f"installed {name}")

    def _ensure_authorized_key(self, add_key: str | None, *, dry_run: bool) -> list[StepResult]:
        ssh_dir = self._home / ".ssh"
        keys = ssh_dir / "authorized_keys"
        out: list[StepResult] = []
        if dry_run:
            out.append(StepResult(level="info", message=f"DRY RUN: ensure {keys} (700/600)"))
        else:
            self._fs.mkdir(ssh_dir)
            if not self._fs.exists(keys):
                self._fs.write_text(keys, "")
            out.append(StepResult(level="success", message="SSH authorized_keys ready"))

        if add_key is None:
            out.append(
                StepResult(
                    level="warn",
                    message="No phone key provided. Rerun with --add-key '<public key>'",
                )
            )
            return out
        if not is_ssh_public_key(add_key):
            raise InvalidKeyError(add_key)
        if dry_run:
            out.append(StepResult(level="info", message="DRY RUN: append phone key if missing"))
            return out
        existing = self._fs.read_text(keys) if self._fs.exists(keys) else ""
        if add_key in existing.splitlines():
            out.append(StepResult(level="success", message="Phone public key already present"))
        else:
            self._fs.write_text(keys, existing + add_key + "\n")
            out.append(StepResult(level="success", message="Added phone public key"))
        return out

    def _enable_remote_login(self, *, dry_run: bool) -> StepResult:
        if self._remote_login_on():
            return StepResult(level="success", message="Remote Login already enabled")
        return self._sudo(("systemsetup", "-setremotelogin", "on"), dry_run=dry_run)

    def _harden(self, harden: bool, *, dry_run: bool) -> list[StepResult]:
        if not harden:
            return [
                StepResult(
                    level="warn",
                    message="SSH password auth unchanged. Rerun with --harden-ssh "
                    "after adding your Termius key",
                )
            ]
        if dry_run:
            return [
                StepResult(
                    level="info", message=f"DRY RUN: write key-only config to {_HARDEN_PATH}"
                ),
                StepResult(level="info", message="DRY RUN: launchctl kickstart sshd"),
            ]
        staging = self._home / ".dotfiles-sshd-remote.conf"
        self._fs.write_text(staging, _HARDEN_CONTENT)
        out = [self._sudo(("mkdir", "-p", _HARDEN_DIR), dry_run=False)]
        out.append(self._sudo(("install", "-m", "644", str(staging), _HARDEN_PATH), dry_run=False))
        out.append(
            self._sudo(("launchctl", "kickstart", "-k", "system/com.openssh.sshd"), dry_run=False)
        )
        out.append(StepResult(level="success", message="SSH hardened for key-only login"))
        return out

    def setup(
        self, *, dry_run: bool, add_key: str | None, harden: bool, session: str
    ) -> list[StepResult]:
        steps = [
            self._ensure_tool("mosh", dry_run=dry_run),
            self._ensure_tool("zellij", dry_run=dry_run),
        ]
        steps.extend(self._ensure_authorized_key(add_key, dry_run=dry_run))
        steps.append(self._enable_remote_login(dry_run=dry_run))
        steps.extend(self._harden(harden, dry_run=dry_run))
        return steps
