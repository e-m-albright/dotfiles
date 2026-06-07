"""Remote-shell setup/disable logic. Pure decisions over the ProcessRunner port."""

import shutil
from collections.abc import Callable
from functools import cached_property
from pathlib import Path

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.remote.models import ConnectionInfo, RemoteStatus
from dotfiles.result import StepResult

_KEY_PREFIXES = ("ssh-ed25519 ", "ssh-rsa ", "ecdsa-sha2-")

# Remote Login is toggled by hand in System Settings, not by this CLI: flipping it
# via `systemsetup` needs the terminal to hold Full Disk Access (macOS 26+), which
# is a standing local-privilege grant we'd rather not require. So we read the state
# and point at the toggle instead of mutating it.
SHARING_HINT = "System Settings → General → Sharing → Remote Login"
_SHARING_URL = "x-apple.systempreferences:com.apple.Sharing-Settings.extension"
SHARING_OPEN = f'open "{_SHARING_URL}"'

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
        interactive: bool,
        home: Path,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self._runner = runner
        self._interactive = interactive
        self._home = home
        self._which = which

    def _line(self, command: tuple[str, ...]) -> str:
        result = self._runner.run(command)
        return result.stdout.strip() if result.ok else ""

    @cached_property
    def _user(self) -> str:
        return self._line(("id", "-un")) or "user"

    @cached_property
    def _host(self) -> str:
        host = self._line(("scutil", "--get", "LocalHostName"))
        return host or self._line(("hostname", "-s")) or "localhost"

    @cached_property
    def _mosh_server(self) -> str:
        if Path("/opt/homebrew/bin/mosh-server").exists():
            return "/opt/homebrew/bin/mosh-server"
        return self._which("mosh-server") or "/opt/homebrew/bin/mosh-server"

    def _remote_login_on(self) -> bool:
        # `systemsetup -getremotelogin` needs admin on macOS 26+ (without sudo it
        # prints "You need administrator access…" and we'd misread it as off).
        # The launchd override is the same state the Sharing pane toggles and is
        # readable without privileges, so a `status` call never needs a password.
        return '"com.openssh.sshd" => enabled' in self._line(
            ("launchctl", "print-disabled", "system")
        )

    def _ssh_password_auth(self) -> bool | None:
        # True if SSH permits password login (password OR keyboard-interactive),
        # False if key-only, None if undetermined. `sshd -G` prints the effective
        # config including drop-ins and, unlike `-T`, doesn't need root — so a
        # status read never costs a password.
        result = self._runner.run(("/usr/sbin/sshd", "-G"))
        if not result.ok:
            return None
        values: dict[str, str] = {}
        for line in result.stdout.splitlines():
            key, _, value = line.partition(" ")
            values[key] = value.strip()
        password = values.get("passwordauthentication")
        if password is None:
            return None
        keyboard = values.get("kbdinteractiveauthentication", "no")
        return password == "yes" or keyboard == "yes"

    @cached_property
    def _tailscale(self) -> tuple[bool, str | None]:
        if self._runner.run(("tailscale", "status")).ok:
            ip = self._line(("tailscale", "ip", "-4"))
            return True, (ip or None)
        return False, None

    def status(self) -> RemoteStatus:
        connected, ip = self._tailscale
        return RemoteStatus(
            remote_login_on=self._remote_login_on(),
            tailscale_connected=connected,
            tailnet_ip=ip,
            host=self._host,
            user=self._user,
            mosh_server=self._mosh_server,
            ssh_password_auth=self._ssh_password_auth(),
        )

    def connection_info(self, session: str) -> ConnectionInfo:
        connected, ip = self._tailscale
        return ConnectionInfo(
            user=self._user,
            host=self._host,
            session=session,
            mosh_server=self._mosh_server,
            tailnet_ip=ip if connected else None,
        )

    def _sudo(self, args: tuple[str, ...], *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(level="info", message="DRY RUN: sudo " + " ".join(args))
        if not (self._interactive or self._runner.run(("sudo", "-n", "true")).ok):
            return StepResult(
                level="warn",
                message="Needs sudo in an interactive terminal. Run manually: sudo "
                + " ".join(args),
            )
        result = self._runner.run(("sudo", *args))
        if result.ok:
            return StepResult(level="success", message="sudo " + " ".join(args))
        detail = (result.stderr.strip() or result.stdout.strip()).splitlines()
        reason = f": {detail[-1].strip()}" if detail else ""
        return StepResult(level="error", message=f"sudo {' '.join(args)} failed{reason}")

    def _ensure_tool(self, name: str, *, dry_run: bool) -> StepResult:
        if self._runner.run((name, "--version")).ok:
            return StepResult(level="success", message=f"{name} available")
        if dry_run:
            return StepResult(level="info", message=f"DRY RUN: brew install {name}")
        result = self._runner.run(("brew", "install", name))
        if not result.ok:
            return StepResult(level="error", message=f"brew install {name} failed")
        return StepResult(level="success", message=f"installed {name}")

    def _write_key(self, keys: Path, add_key: str) -> StepResult:
        existing = keys.read_text() if keys.exists() else ""
        if add_key in existing.splitlines():
            return StepResult(level="success", message="Phone public key already present")
        separator = "" if not existing or existing.endswith("\n") else "\n"
        keys.write_text(existing + separator + add_key + "\n")
        return StepResult(level="success", message="Added phone public key")

    def _existing_key_status(self, keys: Path) -> StepResult:
        """Report keys already in authorized_keys, rather than nagging about the
        --add-key flag — a key added on a prior run is still there."""
        existing = keys.read_text().splitlines() if keys.exists() else []
        authorized = sum(1 for line in existing if is_ssh_public_key(line))
        if authorized:
            return StepResult(
                level="success", message=f"{authorized} phone key(s) already authorized"
            )
        return StepResult(
            level="warn", message="No phone key yet. Rerun with --add-key '<public key>'"
        )

    def _ensure_authorized_key(self, add_key: str | None, *, dry_run: bool) -> list[StepResult]:
        ssh_dir = self._home / ".ssh"
        keys = ssh_dir / "authorized_keys"
        # Fail fast: reject a malformed key before any filesystem mutation, so an
        # invalid key never leaves a freshly-created ~/.ssh/authorized_keys behind.
        if add_key is not None and not is_ssh_public_key(add_key):
            raise InvalidKeyError(add_key)
        out: list[StepResult] = []
        if dry_run:
            out.append(StepResult(level="info", message=f"DRY RUN: ensure {keys} (700/600)"))
        else:
            ssh_dir.mkdir(parents=True, exist_ok=True)
            ssh_dir.chmod(0o700)
            if not keys.exists():
                keys.write_text("")
            keys.chmod(0o600)
            out.append(StepResult(level="success", message="SSH authorized_keys ready"))

        if add_key is None:
            out.append(self._existing_key_status(keys))
            return out
        if dry_run:
            out.append(StepResult(level="info", message="DRY RUN: append phone key if missing"))
            return out
        out.append(self._write_key(keys, add_key))
        return out

    def _enable_remote_login(self, *, dry_run: bool) -> StepResult:
        if self._remote_login_on():
            return StepResult(level="success", message="Remote Login already enabled")
        # We can't flip the toggle (needs Full Disk Access), but we can open the
        # exact Settings pane so it's one tap away instead of a buried path.
        if not dry_run:
            self._runner.run(("open", _SHARING_URL))
        return StepResult(
            level="warn",
            message="Remote Login is off — opened System Settings; flip the Remote Login toggle",
            details=SHARING_HINT,
        )

    def _harden(self, harden: bool, *, dry_run: bool) -> list[StepResult]:
        if not harden:
            # Report the actual effective state, not whether the flag was passed.
            password_auth = self._ssh_password_auth()
            if password_auth is False:
                return [
                    StepResult(level="success", message="SSH already key-only (password auth off)")
                ]
            if password_auth is True:
                return [
                    StepResult(
                        level="warn",
                        message="SSH password auth is ON — rerun with --harden-ssh to disable it",
                    )
                ]
            return [
                StepResult(
                    level="info",
                    message="SSH password-auth state unknown (could not read sshd config)",
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
        staging.write_text(_HARDEN_CONTENT)
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

    def kill_sessions(self, *, dry_run: bool) -> list[StepResult]:
        """Kill existing Mosh/SSH sessions WITHOUT changing Remote Login state."""
        return self._kill_sessions(dry_run=dry_run)

    def _kill_sessions(self, *, dry_run: bool) -> list[StepResult]:
        user = self._user
        if dry_run:
            return [
                StepResult(level="info", message=f"DRY RUN: pkill -u {user} mosh-server"),
                StepResult(level="info", message=f"DRY RUN: pkill -u {user} sshd"),
            ]
        self._runner.run(("pkill", "-u", user, "mosh-server"))
        self._runner.run(("pkill", "-u", user, "sshd"))
        return [StepResult(level="success", message="Existing Mosh/SSH sessions killed")]

    def web_status(self) -> StepResult:
        """Report whether the zellij web server is running (experimental)."""
        result = self._runner.run(("zellij", "web", "--status"))
        detail = (result.stdout or result.stderr).strip()
        if result.ok:
            return StepResult(level="info", message=detail or "Web server running")
        return StepResult(level="info", message="Web server not running")

    def web_start(self) -> StepResult:
        """Start the zellij web server, daemonized (experimental)."""
        result = self._runner.run(("zellij", "web", "-d"))
        if result.ok:
            return StepResult(level="success", message="Web server started (zellij web -d)")
        return StepResult(level="error", message=f"zellij web -d failed: {result.stderr.strip()}")

    def web_stop(self) -> StepResult:
        """Stop the zellij web server (experimental)."""
        result = self._runner.run(("zellij", "web", "--stop"))
        if result.ok:
            return StepResult(level="success", message="Web server stopped")
        return StepResult(level="warn", message="Web server was not running")

    def web_token(self) -> StepResult:
        """Mint a single-use web login token (shown once, cannot be retrieved)."""
        result = self._runner.run(("zellij", "web", "--create-token"))
        if result.ok:
            return StepResult(level="success", message=result.stdout.strip() or "Token created")
        return StepResult(level="error", message=f"Could not create token: {result.stderr.strip()}")

    def disable(self, *, dry_run: bool, kill_sessions: bool) -> list[StepResult]:
        steps: list[StepResult] = []
        if self._remote_login_on():
            steps.append(
                StepResult(
                    level="warn",
                    message="Remote Login is on — turn it off to stop new SSH/Mosh logins",
                    details=f"{SHARING_HINT}  ·  {SHARING_OPEN}",
                )
            )
        else:
            steps.append(StepResult(level="success", message="Remote Login already disabled"))
        if kill_sessions:
            steps.extend(self._kill_sessions(dry_run=dry_run))
        return steps
