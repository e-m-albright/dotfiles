"""zellij session listing/attach logic. Pure over the ProcessRunner port."""

from dotfiles_cli.core.models import Session

_EMPTY_MARKER = "No active zellij sessions found"


def parse_sessions(output: str) -> list[Session]:
    """Parse `zellij list-sessions --no-formatting` output into Session models."""
    if _EMPTY_MARKER in output:
        return []
    sessions: list[Session] = []
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
