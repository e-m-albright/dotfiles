"""zellij session listing/attach logic. Pure over the ProcessRunner port."""

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.session.models import Session
from dotfiles.result import StepResult

_EMPTY_MARKER = "No active zellij sessions found"


class SessionError(RuntimeError):
    """Raised when a zellij session command fails for a real reason (not just 'no sessions')."""


def parse_sessions(output: str) -> list[Session]:
    """Parse `zellij list-sessions --no-formatting` output into Session models."""
    if _EMPTY_MARKER in output:
        return []
    sessions: list[Session] = []
    # zellij names contain no spaces; "EXITED"/"(current)" only appear in the bracketed suffix.
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        sessions.append(
            Session(
                name=line.split()[0],
                running="EXITED" not in line,
                current="(current)" in line,
            )
        )
    return sessions


def layout_name_for(home: Path, name: str) -> str | None:
    """Return `name` if a curated layout file is deployed for it, else None.

    We ship one layout (`mobile`) under ~/.config/zellij/layouts/; any session
    whose name matches a deployed layout gets it applied on first creation.
    """
    return name if (home / ".config" / "zellij" / "layouts" / f"{name}.kdl").is_file() else None


def attach_command(
    name: str, *, exists: bool = False, layout: str | None = None
) -> tuple[str, ...]:
    """The zellij command to reach `name`.

    A layout can only be applied when the session is first created (`zellij
    attach` takes no --layout), so we branch on whether it already exists:
      - layout + absent  -> create it with the layout
      - layout + present -> plain attach (the persisted state already has it)
      - no layout        -> attach, creating if absent (the long-standing form)
    """
    if layout and not exists:
        return ("zellij", "--session", name, "--layout", layout)
    if layout and exists:
        return ("zellij", "attach", name)
    return ("zellij", "attach", "--create", name)


@runtime_checkable
class SessionLauncher(Protocol):
    """Interactive hand-off: pick from a list, and exec into a command."""

    def pick(self, options: Sequence[str]) -> str | None: ...

    def attach(self, command: Sequence[str]) -> None: ...


def list_sessions(runner: ProcessRunner) -> list[Session]:
    """List running zellij sessions via the ProcessRunner port."""
    result = runner.run(("zellij", "list-sessions", "--no-formatting"))
    combined = result.stdout + result.stderr
    if _EMPTY_MARKER not in combined and not result.ok:
        raise SessionError(result.stderr.strip() or "zellij list-sessions failed")
    return parse_sessions(result.stdout)


def kill_session(runner: ProcessRunner, name: str) -> StepResult:
    """Kill a running zellij session via the ProcessRunner port."""
    result = runner.run(("zellij", "kill-session", name))
    if result.ok:
        return StepResult(level="success", message=f"Killed session {name}")
    return StepResult(level="error", message=f"Could not kill session {name}")


def valid_session_name(name: str) -> bool:
    """True if `name` is usable as a zellij session name (non-empty, no whitespace)."""
    return bool(name) and not any(c.isspace() for c in name)


def attached_client_count(runner: ProcessRunner) -> int | None:
    """Clients attached to the *current* session, or None if not inside one.

    `zellij action list-clients` (0.44+) only works from within a session and
    reports that session's clients — one row per client, first column a numeric
    CLIENT_ID. We count digit-led rows so an unexpected format degrades to None
    rather than crashing the TUI. Off-session, zellij exits non-zero -> None.
    """
    result = runner.run(("zellij", "action", "list-clients"))
    if not result.ok:
        return None
    rows = [line.split() for line in result.stdout.splitlines() if line.split()]
    count = sum(1 for cols in rows if cols[0].isdigit())
    return count or None
