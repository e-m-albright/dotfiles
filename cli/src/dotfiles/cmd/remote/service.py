"""Tailscale-direct phone access lifecycle over the ProcessRunner port.

Paseo drives local agents and binds only to the current Tailscale IPv4 address.
Tailscale Serve exposes one loopback-only private site to the tailnet. Paseo's
relay stays disabled, and no terminal-session wrapper is involved.
"""

import plistlib
import re
from functools import cached_property
from pathlib import Path
from typing import cast

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.remote.models import PASEO_PORT, CaffeineStatus, ConnectionInfo, RemoteStatus
from dotfiles.result import StepResult

_PASEO_LABEL = "com.dotfiles.paseo"
_PASEO_BIN = "/Applications/Paseo.app/Contents/Resources/bin/paseo"
_PASEO_BASE_ARGS = [
    _PASEO_BIN,
    "start",
    "--foreground",
    "--no-relay",
]
_PASEO_STOP_COMMAND = (_PASEO_BIN, "daemon", "stop")
_PASEO_SET_PASSWORD_COMMAND = (_PASEO_BIN, "daemon", "set-password")
_PRIVATE_SITE_COMMAND = (
    "tailscale",
    "serve",
    "--https=8443",
    "--bg",
    "--yes",
    "http://127.0.0.1:8765",
)
_PRIVATE_SITE_URL = re.compile(r"https://[^\s/]+:8443")


class RemoteService:
    """Bring the Tailscale-direct Paseo path up, down, and into view."""

    def __init__(self, *, runner: ProcessRunner, home: Path) -> None:
        self._runner = runner
        self._home = home

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
    def _uid(self) -> str:
        return self._line(("id", "-u")) or "0"

    def tailscale_up(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(level="info", message="DRY RUN: tailscale up")
        result = self._runner.run(("tailscale", "up"))
        if result.ok:
            return StepResult(level="success", message="Tailscale up")
        return StepResult(level="error", message=f"tailscale up failed: {result.stderr.strip()}")

    def tailscale_down(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(level="info", message="DRY RUN: tailscale down")
        result = self._runner.run(("tailscale", "down"))
        if result.ok:
            return StepResult(level="success", message="Tailscale down")
        return StepResult(level="error", message=f"tailscale down failed: {result.stderr.strip()}")

    @cached_property
    def _tailscale(self) -> tuple[bool, str | None]:
        if self._runner.run(("tailscale", "status")).ok:
            ip = self._line(("tailscale", "ip", "-4"))
            return True, (ip or None)
        return False, None

    def tailscale_status(self) -> tuple[bool, str | None]:
        return self._tailscale

    def private_site_enable(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(level="info", message="DRY RUN: enable private site on Tailscale")
        result = self._runner.run(_PRIVATE_SITE_COMMAND)
        if result.ok:
            return StepResult(level="success", message="Private site available on Tailscale")
        return StepResult(level="error", message=f"Tailscale Serve failed: {result.stderr.strip()}")

    def private_site_url(self) -> str | None:
        result = self._runner.run(("tailscale", "serve", "status"))
        if not result.ok or "No serve config" in result.stdout:
            return None
        match = _PRIVATE_SITE_URL.search(result.stdout)
        return match.group(0) if match else None

    def _agent_plist(self) -> Path:
        return self._home / "Library" / "LaunchAgents" / f"{_PASEO_LABEL}.plist"

    def _agent_running(self) -> bool:
        for line in self._line(("launchctl", "list")).splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[2] == _PASEO_LABEL:
                return parts[0] != "-"
        return False

    def _render_plist(self, program_args: list[str]) -> bytes:
        log = self._home / "Library" / "Logs" / "paseo.log"
        return plistlib.dumps(
            {
                "Label": _PASEO_LABEL,
                "ProgramArguments": program_args,
                "RunAtLoad": True,
                "KeepAlive": False,
                "StandardOutPath": str(log),
                "StandardErrorPath": str(log),
                "WorkingDirectory": str(self._home),
                "EnvironmentVariables": {
                    "PATH": (
                        f"{self._home}/.local/bin:{self._home}/.npm-global/bin:"
                        "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
                    )
                },
            }
        )

    def _load_agent(self, program_args: list[str], *, dry_run: bool) -> list[StepResult]:
        if dry_run:
            return [
                StepResult(level="info", message=f"DRY RUN: install launchd agent {_PASEO_LABEL}")
            ]
        (self._home / "Library" / "LaunchAgents").mkdir(parents=True, exist_ok=True)
        (self._home / "Library" / "Logs").mkdir(parents=True, exist_ok=True)
        plist = self._agent_plist()
        plist.write_bytes(self._render_plist(program_args))
        out = [StepResult(level="success", message=f"Wrote launchd agent {_PASEO_LABEL}")]
        domain = f"gui/{self._uid}"
        self._runner.run(("launchctl", "bootout", f"{domain}/{_PASEO_LABEL}"))
        result = self._runner.run(("launchctl", "bootstrap", domain, str(plist)))
        if result.ok:
            out.append(StepResult(level="success", message="Paseo daemon loaded (RunAtLoad)"))
        else:
            out.append(
                StepResult(
                    level="error", message=f"launchctl bootstrap failed: {result.stderr.strip()}"
                )
            )
        return out

    def _remove_agent(self, *, dry_run: bool) -> list[StepResult]:
        if dry_run:
            return [
                StepResult(level="info", message=f"DRY RUN: remove launchd agent {_PASEO_LABEL}")
            ]
        self._runner.run(("launchctl", "bootout", f"gui/{self._uid}/{_PASEO_LABEL}"))
        plist = self._agent_plist()
        if plist.exists():
            plist.unlink()
        return [StepResult(level="success", message="Removed Paseo daemon launchd agent")]

    def paseo_install_agent(self, *, dry_run: bool) -> list[StepResult]:
        """Install Paseo bound to the current tailnet IP with relay disabled."""
        if dry_run:
            return self._load_agent(_PASEO_BASE_ARGS, dry_run=True)

        connected, tailnet_ip = self._tailscale
        if not connected or not tailnet_ip:
            return [
                StepResult(
                    level="error",
                    message="Paseo not started: no tailnet IPv4 address is available",
                )
            ]

        self._runner.run(_PASEO_STOP_COMMAND)
        return self._load_agent(
            [*_PASEO_BASE_ARGS, "--listen", f"{tailnet_ip}:{PASEO_PORT}"], dry_run=False
        )

    def _paseo_listen_address(self) -> str | None:
        plist = self._agent_plist()
        if not plist.exists():
            return None
        try:
            data = plistlib.loads(plist.read_bytes())
        except (plistlib.InvalidFileException, ValueError):
            return None
        raw_args = data.get("ProgramArguments")
        if not isinstance(raw_args, list):
            return None
        args = [str(item) for item in cast("list[object]", raw_args)]
        if "--listen" not in args:
            return None
        index = args.index("--listen") + 1
        return args[index] if index < len(args) else None

    def paseo_listen_stale(self) -> bool:
        address = self._paseo_listen_address()
        if address is None:
            return False
        connected, ip = self._tailscale
        if not connected or not ip:
            return False
        return not address.startswith(f"{ip}:")

    def ensure_paseo_agent(self, *, dry_run: bool) -> list[StepResult]:
        if self.paseo_running():
            if self.paseo_listen_stale():
                return [
                    StepResult(
                        level="warn",
                        message="Paseo bound to a stale tailnet IP — reinstalling agent",
                    ),
                    *self.paseo_install_agent(dry_run=dry_run),
                ]
            return [StepResult(level="info", message="Paseo daemon already running")]
        return self.paseo_install_agent(dry_run=dry_run)

    def paseo_uninstall_agent(self, *, dry_run: bool) -> list[StepResult]:
        steps = self._remove_agent(dry_run=dry_run)
        if not dry_run:
            self._runner.run(_PASEO_STOP_COMMAND)
        return steps

    def paseo_rotate_password(self, *, dry_run: bool) -> list[StepResult]:
        if dry_run:
            return [
                StepResult(level="info", message="DRY RUN: prompt for a new Paseo password"),
                StepResult(level="info", message="DRY RUN: reload the Paseo launchd agent"),
            ]

        connected, tailnet_ip = self._tailscale
        if not connected or not tailnet_ip:
            return [
                StepResult(
                    level="error",
                    message="Paseo password not changed: no tailnet IPv4 address is available",
                )
            ]

        updated = self._runner.run(_PASEO_SET_PASSWORD_COMMAND, capture_output=False)
        if not updated.ok:
            return [StepResult(level="error", message="Paseo password update cancelled or failed")]

        steps = [StepResult(level="success", message="Paseo password updated")]
        steps.extend(self.paseo_install_agent(dry_run=False))
        return steps

    def paseo_running(self) -> bool:
        return self._agent_running()

    def caffeine_status(self) -> CaffeineStatus:
        result = self._runner.run(("pmset", "-g", "assertions"))
        if not result.ok:
            return CaffeineStatus(available=False)
        active = "Caffeine is Active" in result.stdout
        return CaffeineStatus(available=True, active=active)

    def status(self) -> RemoteStatus:
        connected, ip = self._tailscale
        return RemoteStatus(
            tailscale_connected=connected,
            tailnet_ip=ip,
            host=self._host,
            user=self._user,
            paseo_running=self.paseo_running(),
            private_site_url=self.private_site_url(),
            caffeine=self.caffeine_status(),
        )

    def connection_info(self) -> ConnectionInfo:
        connected, ip = self._tailscale
        return ConnectionInfo(host=self._host, tailnet_ip=ip if connected else None)
