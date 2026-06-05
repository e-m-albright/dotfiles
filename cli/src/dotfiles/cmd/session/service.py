"""zellij session listing/attach logic. Pure over the ProcessRunner port."""

import re
from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol, runtime_checkable

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.session.models import Session
from dotfiles.result import StepResult

_EMPTY_MARKER = "No active zellij sessions found"

# Default retention for exited sessions: drop those older than 14 days, and keep
# at most the 20 newest. Tunable per call (the `session prune` CLI exposes both).
DEFAULT_MAX_AGE_DAYS = 14
DEFAULT_MAX_COUNT = 20
PRUNE_INTERVAL = timedelta(days=1)

# zellij prints "[Created 10h 40m 27s ago]"; pull the duration out and sum it.
_CREATED_RE = re.compile(r"\[Created (.+?) ago\]")
_UNIT_SECONDS = {"d": 86400, "h": 3600, "m": 60, "s": 1}


def _created_age_seconds(line: str) -> int | None:
    """Seconds since creation parsed from a session's "[Created ... ago]" clause."""
    match = _CREATED_RE.search(line)
    if not match:
        return None
    parts = re.findall(r"(\d+)([dhms])", match.group(1))
    return sum(int(value) * _UNIT_SECONDS[unit] for value, unit in parts) if parts else None


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
                created_age_seconds=_created_age_seconds(line),
            )
        )
    return sessions


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
    """Interactive hand-off: pick from a list, and exec into a command.

    `pick` rows follow a `key<TAB>label` convention: the label is displayed (and may
    carry ANSI colour), but the selected row's key (first tab-field) is returned.
    """

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


def delete_session(runner: ProcessRunner, name: str) -> StepResult:
    """Delete an exited session's serialized state via `zellij delete-session`.

    Valid only for exited (resurrectable) sessions; a running one must be killed.
    """
    result = runner.run(("zellij", "delete-session", name))
    if result.ok:
        return StepResult(level="success", message=f"Deleted session {name}")
    return StepResult(level="error", message=f"Could not delete session {name}")


def prune_exited(runner: ProcessRunner, names: Sequence[str]) -> list[StepResult]:
    """Delete each named (exited) session, returning a StepResult per deletion."""
    return [delete_session(runner, name) for name in names]


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
    runner: ProcessRunner,
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
        sessions = list_sessions(runner)
    except SessionError:
        return []
    names = sessions_to_prune(
        exited_sessions(sessions), max_age_days=max_age_days, max_count=max_count
    )
    results = prune_exited(runner, names)
    _write_prune_stamp(state_file, now)
    return results


def valid_session_name(name: str) -> bool:
    """True if `name` is usable as a zellij session name (non-empty, no whitespace)."""
    return bool(name) and not any(c.isspace() for c in name)


def invalid_session_name_chars(name: str) -> tuple[str, ...]:
    """Human-readable invalid character groups present in *name*."""
    return ("spaces",) if any(c.isspace() for c in name) else ()


def session_name_error(name: str) -> str | None:
    """Validation error for *name*, or None when the characters are valid."""
    invalid = invalid_session_name_chars(name)
    if not invalid:
        return None
    return f"Session name cannot contain {', '.join(invalid)}"


def strip_invalid_session_name_chars(name: str) -> str:
    """Drop characters zellij session names cannot contain."""
    return "".join(c for c in name if not c.isspace())


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
