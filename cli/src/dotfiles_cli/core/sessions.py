"""zellij session listing/attach logic. Pure over the ProcessRunner port."""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from dotfiles_cli.core.models import Session, StepResult
from dotfiles_cli.core.ports import ProcessRunner

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


def attach_command(name: str) -> tuple[str, ...]:
    """The zellij command that attaches to `name`, creating it if absent."""
    # keep in sync with the other zellij attach-command representation
    return ("zellij", "attach", "--create", name)


@runtime_checkable
class SessionLauncher(Protocol):
    """Interactive hand-off: pick from a list, and exec into a command."""

    def pick(self, options: Sequence[str]) -> str | None: ...

    def attach(self, command: Sequence[str]) -> None: ...


class SessionService:
    """Lists and kills zellij sessions via the ProcessRunner port."""

    def __init__(self, *, runner: ProcessRunner) -> None:
        self._runner = runner

    def list(self) -> list[Session]:
        result = self._runner.run(("zellij", "list-sessions", "--no-formatting"))
        combined = result.stdout + result.stderr
        if _EMPTY_MARKER not in combined and not result.ok:
            raise SessionError(result.stderr.strip() or "zellij list-sessions failed")
        return parse_sessions(combined)

    def kill(self, name: str) -> StepResult:
        result = self._runner.run(("zellij", "kill-session", name))
        if result.ok:
            return StepResult(level="success", message=f"Killed session {name}")
        return StepResult(level="error", message=f"Could not kill session {name}")
