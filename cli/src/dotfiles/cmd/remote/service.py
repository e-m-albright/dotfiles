"""Remote phone-access logic. Pure decisions over the ProcessRunner port.

The stack: Tailscale (private network) + two phone surfaces — **Paseo** (primary;
a daemon driving Pi/Claude Code/Codex, reached directly over the tailnet by the
Paseo app) and the **Zellij web client** (fallback browser terminal, exposed with
`tailscale serve`). Both are kept alive by launchd agents this module owns.
SSH/Mosh and ygncode were retired.
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
# tailnet with `tailscale serve`. A launchd agent keeps it running.
ZELLIJ_WEB_PORT = 8082
_ZELLIJ_BIN = "/opt/homebrew/bin/zellij"
_ZELLIJ_LABEL = "com.dotfiles.zellij-web"

# Paseo — the primary phone driver (multi-agent daemon incl. Pi). It binds only
# to this machine's Tailscale IPv4; all clients connect DIRECTLY over the
# tailnet with the daemon password (no `tailscale serve`, no token/URL).
#
# WARNING — TAILSCALE-ONLY BY DESIGN. Never enable Paseo's relay (config
# `relay.enabled` or dropping `--no-relay` below): it holds a persistent
# outbound connection to relay.paseo.sh, moving access outside the tailnet.
# We tried it once for QR phone pairing (2026-07) and reverted; the QR
# convenience is not worth the exposure. Phones get the password manually.
#
# `paseo` is an fnm-managed npm global, so launchd asks fnm to run it
# under the current default Node version. The daemon password lives hashed in
# ~/.paseo — never in the plist.
PASEO_PORT = 6767
_PASEO_LABEL = "com.dotfiles.paseo"
_FNM_BIN = "/opt/homebrew/bin/fnm"
_PASEO_BASE_ARGS = [
    _FNM_BIN,
    "exec",
    "--using=default",
    "paseo",
    "start",
    "--foreground",
    "--no-relay",
]
_PASEO_STOP_COMMAND = (
    _FNM_BIN,
    "exec",
    "--using=default",
    "paseo",
    "daemon",
    "stop",
)
_PASEO_SET_PASSWORD_COMMAND = (
    _FNM_BIN,
    "exec",
    "--using=default",
    "paseo",
    "daemon",
    "set-password",
)

# The persistent Zellij session the phone deep-links to (…/mobile), built from
# terminal/zellij/layouts/mobile.kdl.
MOBILE_SESSION = "mobile"


class RemoteService:
    """Brings phone access up/down over the ProcessRunner port."""

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

    def tailscale_status(self) -> tuple[bool, str | None]:
        """Return whether this machine is connected and its tailnet IPv4 address."""
        return self._tailscale

    @cached_property
    def _magic_dns(self) -> str | None:
        """The machine's full MagicDNS name (host.tailnet.ts.net), if on a tailnet."""
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
        """Stop exposing the Zellij web client over the tailnet (leaves it running)."""
        if dry_run:
            return StepResult(level="info", message="DRY RUN: tailscale serve reset")
        result = self._runner.run(("tailscale", "serve", "reset"))
        if result.ok:
            return StepResult(level="success", message="Stopped exposing Zellij web (serve reset)")
        return StepResult(level="warn", message="Nothing was being served")

    # --- launchd agents ----------------------------------------------------

    def _agent_plist(self, label: str) -> Path:
        return self._home / "Library" / "LaunchAgents" / f"{label}.plist"

    def _agent_running(self, label: str) -> bool:
        return label in self._line(("launchctl", "list"))

    def _render_plist(
        self,
        label: str,
        program_args: list[str],
        log_name: str,
        *,
        environment: dict[str, str] | None = None,
        interactive: bool = False,
        keep_alive: bool = True,
    ) -> bytes:
        # Built at runtime from self._home, so no absolute home path is ever
        # committed to the repo (this file stays path-neutral).
        log = self._home / "Library" / "Logs" / log_name
        plist: dict[str, object] = {
            "Label": label,
            "ProgramArguments": program_args,
            "RunAtLoad": True,
            "KeepAlive": keep_alive,
            "StandardOutPath": str(log),
            "StandardErrorPath": str(log),
            "WorkingDirectory": str(self._home),
        }
        if environment:
            plist["EnvironmentVariables"] = environment
        if interactive:
            plist["EnvironmentVariables"] = {
                "PATH": "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
            }
            plist["ProcessType"] = "Interactive"
        return plistlib.dumps(plist)

    def _load_agent(
        self,
        label: str,
        program_args: list[str],
        log_name: str,
        name: str,
        *,
        dry_run: bool,
        environment: dict[str, str] | None = None,
        interactive: bool = False,
        keep_alive: bool = True,
    ) -> list[StepResult]:
        """Write a runtime-rendered launchd plist and bootstrap it. Idempotent."""
        if dry_run:
            return [StepResult(level="info", message=f"DRY RUN: install launchd agent {label}")]
        (self._home / "Library" / "LaunchAgents").mkdir(parents=True, exist_ok=True)
        (self._home / "Library" / "Logs").mkdir(parents=True, exist_ok=True)
        plist = self._agent_plist(label)
        plist.write_bytes(
            self._render_plist(
                label,
                program_args,
                log_name,
                environment=environment,
                interactive=interactive,
                keep_alive=keep_alive,
            )
        )
        out = [StepResult(level="success", message=f"Wrote launchd agent {label}")]
        domain = f"gui/{self._uid}"
        self._runner.run(("launchctl", "bootout", f"{domain}/{label}"))  # ignore if absent
        result = self._runner.run(("launchctl", "bootstrap", domain, str(plist)))
        if result.ok:
            lifecycle = "RunAtLoad + KeepAlive" if keep_alive else "RunAtLoad"
            out.append(StepResult(level="success", message=f"{name} loaded ({lifecycle})"))
        else:
            out.append(
                StepResult(
                    level="error", message=f"launchctl bootstrap failed: {result.stderr.strip()}"
                )
            )
        return out

    def _remove_agent(self, label: str, name: str, *, dry_run: bool) -> list[StepResult]:
        if dry_run:
            return [StepResult(level="info", message=f"DRY RUN: remove launchd agent {label}")]
        self._runner.run(("launchctl", "bootout", f"gui/{self._uid}/{label}"))
        plist = self._agent_plist(label)
        if plist.exists():
            plist.unlink()
        return [StepResult(level="success", message=f"Removed {name} launchd agent ({label})")]

    # Zellij web (fallback terminal) --------------------------------------

    def install_agent(self, *, dry_run: bool) -> list[StepResult]:
        """Install + load the launchd agent that keeps the Zellij web server alive."""
        return self._load_agent(
            _ZELLIJ_LABEL,
            [_ZELLIJ_BIN, "web", "--start"],
            "zellij-web.log",
            "Zellij web",
            dry_run=dry_run,
            interactive=True,
        )

    def ensure_zellij_agent(self, *, dry_run: bool) -> list[StepResult]:
        """Load the managed Zellij web service only when it is not already running."""
        if self._agent_running(_ZELLIJ_LABEL):
            return [StepResult(level="info", message="Zellij web already running")]
        return self.install_agent(dry_run=dry_run)

    def uninstall_agent(self, *, dry_run: bool) -> list[StepResult]:
        """Unload + remove the Zellij web launchd agent."""
        return self._remove_agent(_ZELLIJ_LABEL, "Zellij web", dry_run=dry_run)

    def zellij_web_running(self) -> bool:
        return self._runner.run(("zellij", "web", "--status")).ok

    # Paseo (primary agent daemon) ----------------------------------------

    def paseo_install_agent(self, *, dry_run: bool) -> list[StepResult]:
        """Install + load the launchd agent that keeps the Paseo daemon alive.

        Runs `paseo start --no-relay …` through fnm's current default Node
        version. No secret is written — the daemon password is stored hashed in
        ~/.paseo by `paseo daemon set-password`.
        """
        if dry_run:
            return self._load_agent(
                _PASEO_LABEL,
                _PASEO_BASE_ARGS,
                "paseo.log",
                "Paseo daemon",
                dry_run=True,
                keep_alive=False,
            )

        connected, tailnet_ip = self._tailscale
        if not connected or not tailnet_ip:
            return [
                StepResult(
                    level="error",
                    message="Paseo not started: no tailnet IPv4 address is available",
                )
            ]

        # Older launchd definitions started Paseo in detached mode, leaving a
        # daemon outside launchd's lifecycle. Stop that process before loading
        # the foreground-owned replacement; no daemon running is a harmless case.
        self._runner.run(_PASEO_STOP_COMMAND)
        return self._load_agent(
            _PASEO_LABEL,
            [*_PASEO_BASE_ARGS, "--listen", f"{tailnet_ip}:{PASEO_PORT}"],
            "paseo.log",
            "Paseo daemon",
            dry_run=False,
            environment={
                # ~/.npm-global/bin carries npm-prefix globals (pi, paseo);
                # without it the daemon reports "Provider 'pi' is not available".
                "PATH": (
                    f"{self._home}/.local/bin:{self._home}/.npm-global/bin:"
                    "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
                )
            },
            keep_alive=False,
        )

    def ensure_paseo_agent(self, *, dry_run: bool) -> list[StepResult]:
        """Load the managed Paseo daemon only when it is not already running."""
        if self.paseo_running():
            return [StepResult(level="info", message="Paseo daemon already running")]
        return self.paseo_install_agent(dry_run=dry_run)

    def paseo_uninstall_agent(self, *, dry_run: bool) -> list[StepResult]:
        """Unload + remove the Paseo launchd agent and any legacy detached daemon."""
        steps = self._remove_agent(_PASEO_LABEL, "Paseo daemon", dry_run=dry_run)
        if not dry_run:
            self._runner.run(_PASEO_STOP_COMMAND)
        return steps

    def paseo_rotate_password(self, *, dry_run: bool) -> list[StepResult]:
        """Prompt securely for a new daemon password, then reload the managed daemon."""
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
        return self._agent_running(_PASEO_LABEL)

    def mobile_session_step(self, *, dry_run: bool) -> StepResult:
        """Ensure the `mobile` Zellij session exists; guide creation if not.

        Zellij only creates a session on attach (it needs a PTY), so we don't
        spawn one non-interactively — we surface the one-time create command.
        """
        if dry_run:
            return StepResult(level="info", message=f"DRY RUN: check '{MOBILE_SESSION}' session")
        result = self._runner.run(("zellij", "list-sessions", "--no-formatting"))
        names = (
            [line.split()[0] for line in result.stdout.splitlines() if line.strip()]
            if result.ok
            else []
        )
        if MOBILE_SESSION in names:
            return StepResult(level="success", message=f"'{MOBILE_SESSION}' session ready")
        return StepResult(
            level="warn",
            message=(
                f"No '{MOBILE_SESSION}' session yet — create it once: "
                f"zellij --session {MOBILE_SESSION} --layout {MOBILE_SESSION} (detach: Ctrl-o d)"
            ),
        )

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
            paseo_running=self.paseo_running(),
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

    def web_token(self) -> StepResult:
        """Mint a single-use web login token (shown once, cannot be retrieved)."""
        result = self._runner.run(("zellij", "web", "--create-token"))
        if result.ok:
            return StepResult(level="success", message=result.stdout.strip() or "Token created")
        return StepResult(level="error", message=f"Could not create token: {result.stderr.strip()}")
