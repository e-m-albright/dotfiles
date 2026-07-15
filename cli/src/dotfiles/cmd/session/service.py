"""Session-management policy: retention selection and the interactive hand-off.

zellij-specific knowledge (commands, output/cache format, paths) lives in
`zellij.py`; this module is the host-agnostic policy on top of it — what counts
as prunable — plus the `SessionLauncher` seam for the interactive pick/exec
hand-off (which is fzf/exec, not zellij).
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from dotfiles.cmd.session.models import Session

# Default retention for exited sessions: drop those older than 14 days, and keep
# at most the 20 newest. Tunable per call (the `session prune` CLI exposes both).
DEFAULT_MAX_AGE_DAYS = 14
DEFAULT_MAX_COUNT = 20


def humanize_age(seconds: int | None) -> str:
    """Compact age string using the largest whole unit: "2d", "1h", "30m", "45s"."""
    if seconds is None:
        return "?"
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= size:
            return f"{seconds // size}{unit}"
    return f"{seconds}s"


def exited_sessions(sessions: Sequence[Session]) -> list[Session]:
    """Exited (resurrectable) sessions only, newest-first; unknown age sorts last."""
    exited = (s for s in sessions if not s.running)
    return sorted(exited, key=lambda s: (s.created_age_seconds is None, s.created_age_seconds or 0))


def sessions_to_prune(exited: Sequence[Session], *, max_age_days: int, max_count: int) -> list[str]:
    """Names of exited sessions to delete: those older than *max_age_days*.

    Sessions with unknown age are never dropped by the age rule.
    """
    ordered = exited_sessions(exited)
    max_age_seconds = max_age_days * 86400
    doomed = {
        s.name
        for i, s in enumerate(ordered)
        if i >= max_count
        or (s.created_age_seconds is not None and s.created_age_seconds > max_age_seconds)
    }
    return [s.name for s in ordered if s.name in doomed]


@runtime_checkable
class SessionLauncher(Protocol):
    """Interactive hand-off: pick from a list, and exec into a command.

    `pick` rows follow a `key<TAB>label` convention: the label is displayed (and may
    carry ANSI colour), but the selected row's key (first tab-field) is returned.
    """

    def pick(self, options: Sequence[str]) -> str | None: ...

    def attach(self, command: Sequence[str]) -> None: ...
