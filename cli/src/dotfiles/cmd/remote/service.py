"""Remote phone-access logic. Pure decisions over the ProcessRunner port.

The stack: Tailscale (private network) + two browser surfaces served over the
tailnet — the **Zellij web client** (fallback terminal, kept alive by a launchd
agent this module owns) and **ygncode pi-web** (the primary Pi PWA, which manages
its own launchd service + `tailscale serve`). SSH/Mosh were retired.
"""

import json
import plistlib
from functools import cached_property
from pathlib import Path
from typing import cast

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.remote.models import ConnectionInfo, RemoteStatus
from dotfiles.result import StepResult

# Zellij web client — the fallback browser terminal on localhost, exposed to the
# tailnet with `tailscale serve`. A launchd agent (below) keeps it running.
ZELLIJ_WEB_PORT = 8082
_ZELLIJ_BIN = "/opt/homebrew/bin/zellij"
_AGENT_LABEL = "com.dotfiles.zellij-web"

# ygncode pi-web — the primary Pi PWA. It installs & manages its own launchd
# service (com.pi-web) and its own `tailscale serve` route on this port. We only
# ensure it's running and point at how to install it (Workbench owns the install).
PI_WEB_LABEL = "com.pi-web"
PI_WEB_PORT = 31415
_PI_WEB_INSTALL = "pi install npm:@ygncode/pi-web@0.0.1-beta.34"


class RemoteService:
    """Brings phone web-access up/down over the ProcessRunner port."""

    def __init__(self, *, runner: ProcessRunner, interactive: bool, home: Path) -> None:
        self._runner = runner
        self._interactive = interactive
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

    # --- Tailscale ---------------------------------------------------------

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

    @cached_property
    def _tailscale(self) -> tuple[bool, str | None]:
        if self._runner.run(("tailscale", "status")).ok:
            ip = self._line(("tailscale", "ip", "-4"))
            return True, (ip or None)
        return False, None

    @cached_property
    def _magic_dns(self) -> str | None:
        """The machine's full MagicDNS name (host.tailnet.ts.net), if on a tailnet.

        `tailscale serve` issues its TLS cert for this name, so it's what the
        phone's browser must open. None off-tailnet or if the query fails.
        """
        result = self._runner.run(("tailscale", "status", "--json"))
        if not result.ok:
            return None
        try:
            raw: object = json.loads(result.stdout)
        except (ValueError, TypeError):
            return None
        if not isinstance(raw, dict):
            return None
        self_node = cast("dict[str, object]", raw).get("Self")
        if not isinstance(self_node, dict):
            return None
        name = cast("dict[str, object]", self_node).get("DNSName")
        if not isinstance(name, str):
            return None
        return name.rstrip(".") or None

    def serve_start(self, *, dry_run: bool) -> StepResult:
        """Expose the Zellij web client to the tailnet (TLS terminated by Tailscale)."""
        if dry_run:
            return StepResult(
                level="info", message=f"DRY RUN: tailscale serve --bg {ZELLIJ_WEB_PORT}"
            )
        result = self._runner.run(("tailscale", "serve", "--bg", str(ZELLIJ_WEB_PORT)))
        if result.ok:
            return StepResult(
                level="success",
                message=f"Zellij web exposed on the tailnet (tailscale serve :{ZELLIJ_WEB_PORT})",
            )
        return StepResult(level="error", message=f"tailscale serve failed: {result.stderr.strip()}")

    def serve_reset(self, *, dry_run: bool) -> StepResult:
        """Stop exposing the web clients over the tailnet (leaves the servers running)."""
        if dry_run:
            return StepResult(level="info", message="DRY RUN: tailscale serve reset")
        result = self._runner.run(("tailscale", "serve", "reset"))
        if result.ok:
            return StepResult(level="success", message="Stopped exposing web clients (serve reset)")
        return StepResult(level="warn", message="Nothing was being served")

    # --- Zellij web launchd agent ------------------------------------------

    @property
    def _agent_plist(self) -> Path:
        return self._home / "Library" / "LaunchAgents" / f"{_AGENT_LABEL}.plist"

    def _render_agent_plist(self) -> bytes:
        # Built at runtime from self._home, so no absolute home path is ever
        # committed to the repo (this file stays path-neutral).
        log = self._home / "Library" / "Logs" / "zellij-web.log"
        plist: dict[str, object] = {
            "Label": _AGENT_LABEL,
            "ProgramArguments": [_ZELLIJ_BIN, "web", "--start"],
            "EnvironmentVariables": {"PATH": "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"},
            "RunAtLoad": True,
            "KeepAlive": True,
            "ProcessType": "Interactive",
            "StandardOutPath": str(log),
            "StandardErrorPath": str(log),
            "WorkingDirectory": str(self._home),
        }
        return plistlib.dumps(plist)

    def install_agent(self, *, dry_run: bool) -> list[StepResult]:
        """Install + load the launchd agent that keeps the Zellij web server alive.

        Idempotent: bootout any prior copy, then bootstrap the freshly written plist.
        """
        if dry_run:
            return [
                StepResult(level="info", message=f"DRY RUN: install launchd agent {_AGENT_LABEL}")
            ]
        (self._home / "Library" / "LaunchAgents").mkdir(parents=True, exist_ok=True)
        (self._home / "Library" / "Logs").mkdir(parents=True, exist_ok=True)
        self._agent_plist.write_bytes(self._render_agent_plist())
        out = [StepResult(level="success", message=f"Wrote launchd agent {_AGENT_LABEL}")]
        domain = f"gui/{self._uid}"
        self._runner.run(("launchctl", "bootout", f"{domain}/{_AGENT_LABEL}"))  # ignore if absent
        result = self._runner.run(("launchctl", "bootstrap", domain, str(self._agent_plist)))
        if result.ok:
            out.append(
                StepResult(
                    level="success", message="Zellij web agent loaded (RunAtLoad + KeepAlive)"
                )
            )
        else:
            out.append(
                StepResult(
                    level="error", message=f"launchctl bootstrap failed: {result.stderr.strip()}"
                )
            )
        return out

    def uninstall_agent(self, *, dry_run: bool) -> list[StepResult]:
        """Unload + remove the Zellij web launchd agent."""
        if dry_run:
            return [
                StepResult(level="info", message=f"DRY RUN: remove launchd agent {_AGENT_LABEL}")
            ]
        self._runner.run(("launchctl", "bootout", f"gui/{self._uid}/{_AGENT_LABEL}"))
        if self._agent_plist.exists():
            self._agent_plist.unlink()
        return [StepResult(level="success", message=f"Removed launchd agent {_AGENT_LABEL}")]

    def zellij_web_running(self) -> bool:
        return self._runner.run(("zellij", "web", "--status")).ok

    # --- ygncode pi-web (primary Pi PWA) -----------------------------------

    def pi_web_installed(self) -> bool:
        return (self._home / ".pi" / "agent" / "bin" / "pi-web").exists()

    def pi_web_running(self) -> bool:
        return PI_WEB_LABEL in self._line(("launchctl", "list"))

    def pi_web_kick(self, *, dry_run: bool) -> StepResult:
        """(Re)start ygncode's pi-web service, or point at how to install it."""
        if not self.pi_web_installed():
            return StepResult(
                level="warn",
                message=f"ygncode pi-web not installed — install via Workbench ({_PI_WEB_INSTALL})",
            )
        if dry_run:
            return StepResult(level="info", message=f"DRY RUN: launchctl kickstart {PI_WEB_LABEL}")
        result = self._runner.run(
            ("launchctl", "kickstart", "-k", f"gui/{self._uid}/{PI_WEB_LABEL}")
        )
        if result.ok:
            return StepResult(
                level="success", message=f"ygncode pi-web (re)started on :{PI_WEB_PORT}"
            )
        return StepResult(level="error", message=f"Could not start pi-web: {result.stderr.strip()}")

    def pi_web_token(self) -> str | None:
        """Read ygncode pi-web's login token from ~/.config/pi-web/env (or None)."""
        env = self._home / ".config" / "pi-web" / "env"
        if not env.exists():
            return None
        for line in env.read_text().splitlines():
            if line.startswith("PI_WEB_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"') or None
        return None

    # --- status / connection ----------------------------------------------

    def status(self) -> RemoteStatus:
        connected, ip = self._tailscale
        return RemoteStatus(
            tailscale_connected=connected,
            tailnet_ip=ip,
            host=self._host,
            user=self._user,
            magic_dns=self._magic_dns if connected else None,
            zellij_web_running=self.zellij_web_running(),
            pi_web_installed=self.pi_web_installed(),
            pi_web_running=self.pi_web_running(),
        )

    def connection_info(self, session: str) -> ConnectionInfo:
        connected, ip = self._tailscale
        return ConnectionInfo(
            host=self._host,
            session=session,
            tailnet_ip=ip if connected else None,
            magic_dns=self._magic_dns if connected else None,
        )

    # --- Zellij web token helpers -----------------------------------------

    def web_status(self) -> StepResult:
        """Report whether the zellij web server is running."""
        result = self._runner.run(("zellij", "web", "--status"))
        detail = (result.stdout or result.stderr).strip()
        if result.ok:
            return StepResult(level="info", message=detail or "Web server running")
        return StepResult(level="info", message="Web server not running")

    def web_start(self) -> StepResult:
        """Start the zellij web server, daemonized (manual; the launchd agent is preferred)."""
        result = self._runner.run(("zellij", "web", "-d"))
        if result.ok:
            return StepResult(level="success", message="Web server started (zellij web -d)")
        return StepResult(level="error", message=f"zellij web -d failed: {result.stderr.strip()}")

    def web_stop(self) -> StepResult:
        """Stop the zellij web server."""
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
