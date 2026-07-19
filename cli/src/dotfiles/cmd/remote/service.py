"""Remote-shell setup/disable logic. Pure decisions over the ProcessRunner port."""

import shutil
import time
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
# Breadcrumb for the field-column layout (System Settings is implied by context).
SHARING_PATH = "General → Sharing → Remote Login"
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
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._runner = runner
        self._interactive = interactive
        self._home = home
        self._which = which
        # Injectable clock/sleep so the toggle-poll loop is unit-testable without
        # real waiting (a fake runner flips its scripted state across calls).
        self._sleep = sleep
        self._monotonic = monotonic

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

    def remote_login_on(self) -> bool:
        # `systemsetup -getremotelogin` needs admin on macOS 26+ (without sudo it
        # prints "You need administrator access…" and we'd misread it as off).
        # The launchd override is the same state the Sharing pane toggles and is
        # readable without privileges, so a `status` call never needs a password.
        return '"com.openssh.sshd" => enabled' in self._line(
            ("launchctl", "print-disabled", "system")
        )

    def open_sharing_pane(self) -> None:
        """Open the System Settings → Sharing pane so the toggle is one tap away.

        We can't flip Remote Login ourselves (needs Full Disk Access), so both
        `on` and `off` surface the exact pane instead of a buried path.
        """
        self._runner.run(("open", _SHARING_URL))

    def wait_until_remote_login(
        self, target: bool, *, timeout: float = 120.0, poll: float = 1.0
    ) -> bool:
        """Block until Remote Login reaches *target*. True if it flipped, False on timeout.

        Returns immediately when already at *target* (no sleep). The clock and
        sleep are injected, so tests drive this without real time passing.
        """
        deadline = self._monotonic() + timeout
        while True:
            if self.remote_login_on() is target:
                return True
            if self._monotonic() >= deadline:
                return False
            self._sleep(poll)

    def tailscale_up(self, *, dry_run: bool) -> StepResult:
        """Bring the tailnet up so the Mac is reachable away from its home Wi-Fi."""
        if dry_run:
            return StepResult(level="info", message="DRY RUN: tailscale up")
        result = self._runner.run(("tailscale", "up"))
        if result.ok:
            return StepResult(level="success", message="Tailscale up")
        return StepResult(level="error", message=f"tailscale up failed: {result.stderr.strip()}")

    def tailscale_down(self, *, dry_run: bool) -> StepResult:
        """Bring the tailnet down (LAN access over Wi-Fi is unaffected)."""
        if dry_run:
            return StepResult(level="info", message="DRY RUN: tailscale down")
        result = self._runner.run(("tailscale", "down"))
        if result.ok:
            return StepResult(level="success", message="Tailscale down")
        return StepResult(level="error", message=f"tailscale down failed: {result.stderr.strip()}")

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
            remote_login_on=self.remote_login_on(),
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
        if self.remote_login_on():
            return StepResult(level="success", message="Remote Login already enabled")
        if not dry_run:
            self.open_sharing_pane()
        return StepResult(
            level="warn",
            message="Remote Login is off — opened System Settings; flip the Remote Login toggle",
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
        out: list[StepResult] = []
        for command in (
            ("mkdir", "-p", _HARDEN_DIR),
            ("install", "-m", "644", str(staging), _HARDEN_PATH),
            ("launchctl", "kickstart", "-k", "system/com.openssh.sshd"),
        ):
            step = self._sudo(command, dry_run=False)
            out.append(step)
            if step.level in ("error", "warn"):
                return out
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
        user = self._user
        if dry_run:
            return [
                StepResult(level="info", message=f"DRY RUN: pkill -u {user} mosh-server"),
                StepResult(level="info", message=f"DRY RUN: pkill -u {user} sshd"),
            ]
        steps: list[StepResult] = []
        for process in ("mosh-server", "sshd"):
            result = self._runner.run(("pkill", "-u", user, process))
            if result.exit_code == 0:
                steps.append(
                    StepResult(level="success", message=f"Killed existing {process} sessions")
                )
            elif result.exit_code == 1:
                steps.append(
                    StepResult(level="info", message=f"No {process} sessions were running")
                )
            else:
                detail = result.stderr.strip() or f"exit {result.exit_code}"
                steps.append(
                    StepResult(level="error", message=f"Could not kill {process}: {detail}")
                )
        return steps

    def disable_intro(self, *, dry_run: bool, kill_sessions: bool) -> list[StepResult]:
        """Side-effect steps for `off`: optionally kill live sessions.

        The Remote Login status line + Settings/Tailscale fields are presentation,
        rendered by the CLI from a status snapshot — this returns only the
        action steps (session teardown) so the command stays declarative.
        """
        return self.kill_sessions(dry_run=dry_run) if kill_sessions else []

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
