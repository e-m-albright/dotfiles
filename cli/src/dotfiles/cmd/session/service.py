"""Session-management policy: retention sweeps and the interactive hand-off.

zellij-specific knowledge (commands, output/cache format, paths) lives in
`zellij.py`; this module is the host-agnostic policy on top of it — what counts
as prunable, how often to sweep — plus the `SessionLauncher` seam for the
interactive pick/exec hand-off (which is fzf/exec, not zellij).
"""

from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol, runtime_checkable

from dotfiles.cmd.session.models import Session
from dotfiles.cmd.session.zellij import SessionError, Zellij
from dotfiles.result import StepResult

# Default retention for exited sessions: drop those older than 14 days, and keep
# at most the 20 newest. Tunable per call (the `session prune` CLI exposes both).
DEFAULT_MAX_AGE_DAYS = 14
DEFAULT_MAX_COUNT = 20
PRUNE_INTERVAL = timedelta(days=1)


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


def should_prune(last_run: datetime | None, now: datetime, interval: timedelta) -> bool:
    """True if the guarded prune sweep is due (never run, or older than *interval*)."""
    return last_run is None or (now - last_run) >= interval


@runtime_checkable
class SessionLauncher(Protocol):
    """Interactive hand-off: pick from a list, and exec into a command.

    `pick` rows follow a `key<TAB>label` convention: the label is displayed (and may
    carry ANSI colour), but the selected row's key (first tab-field) is returned.
    """

    def pick(self, options: Sequence[str]) -> str | None: ...

    def attach(self, command: Sequence[str]) -> None: ...


def _read_prune_stamp(state_file: Path) -> datetime | None:
    """Last sweep time from *state_file*, or None if missing/unreadable."""
    try:
        return datetime.fromisoformat(state_file.read_text().strip())
    except (OSError, ValueError):
        return None


def _write_prune_stamp(state_file: Path, now: datetime) -> None:
    """Best-effort: an unwritable state dir just means we re-sweep next time."""
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(now.isoformat())
    except OSError:
        pass


def maybe_prune(
    zellij: Zellij,
    *,
    state_file: Path,
    now: datetime,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    max_count: int = DEFAULT_MAX_COUNT,
    interval: timedelta = PRUNE_INTERVAL,
) -> list[StepResult]:
    """Run the retention sweep at most once per *interval* (guarded by *state_file*).

    A no-op when not due. When due, lists sessions, deletes exited ones that breach
    the age/count policy, and stamps the run (even if nothing was deleted, so a
    quiet sweep still resets the clock). zellij being unavailable is swallowed.
    """
    if not should_prune(_read_prune_stamp(state_file), now, interval):
        return []
    try:
        sessions = zellij.list_sessions()
    except SessionError:
        return []
    names = sessions_to_prune(
        exited_sessions(sessions), max_age_days=max_age_days, max_count=max_count
    )
    results = zellij.prune(names)
    _write_prune_stamp(state_file, now)
    return results
