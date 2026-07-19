"""Everything this CLI knows about talking to zellij — in one place.

zellij is reached two ways: its CLI (``list-sessions``/``kill-session``/
``delete-session``/``action list-clients``) and its *undocumented* on-disk cache
of per-session pane state. The binary name, command flags, list-output format,
cache layout, and OS-specific cache path all live here, behind one `Zellij`
facade, so callers work in terms of sessions rather than zellij internals.

The cache reads degrade silently to empty: a zellij format or path change should
drop a preview line, never break the deck. The module-level `parse_*` helpers are
the pure format knowledge (unit-tested directly); `Zellij` binds the
ProcessRunner port and host paths and does the I/O on top of them.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.session.models import Session
from dotfiles.result import StepResult

_EMPTY_MARKER = "No active zellij sessions found"

# zellij prints "[Created 10h 40m 27s ago]"; pull the duration out and sum it.
_CREATED_RE = re.compile(r"\[Created (.+?) ago\]")
_UNIT_SECONDS = {"d": 86400, "h": 3600, "m": 60, "s": 1}

# Pane blocks in session-metadata.kdl carry these one-per-line fields.
_PLUGIN = re.compile(r"\bis_plugin\s+true\b")
_SUPPRESSED = re.compile(r"\bis_suppressed\s+true\b")
_EXITED = re.compile(r"\bexited\s+true\b")
_TITLE = re.compile(r'\btitle\s+"([^"]*)"')


class SessionError(RuntimeError):
    """Raised when a zellij session command fails for a real reason (not just 'no sessions')."""


# --- list-output format (pure) ----------------------------------------------


def _created_age_seconds(line: str) -> int | None:
    """Seconds since creation parsed from a session's "[Created ... ago]" clause."""
    match = _CREATED_RE.search(line)
    if not match:
        return None
    parts = re.findall(r"(\d+)([dhms])", match.group(1))
    return sum(int(value) * _UNIT_SECONDS[unit] for value, unit in parts) if parts else None


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


# --- command/path builders (pure) -------------------------------------------


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
    if layout:
        return ("zellij", "attach", name)
    return ("zellij", "attach", "--create", name)


def layout_name_for(home: Path, name: str) -> str | None:
    """Return `name` if a curated layout file is deployed for it, else None.

    We ship one layout (`mobile`) under ~/.config/zellij/layouts/; any session
    whose name matches a deployed layout gets it applied on first creation.
    """
    return name if (home / ".config" / "zellij" / "layouts" / f"{name}.kdl").is_file() else None


def handoff_command(name: str, *, in_zellij: bool) -> tuple[str, ...]:
    """Command to reach session `name` from the TUI on exit.

    Inside an existing zellij ($ZELLIJ set) we switch sessions in place; otherwise
    we attach (creating if absent). Kept pure so it is unit-testable without a TTY.
    """
    if in_zellij:
        return ("zellij", "action", "switch-session", name)
    return ("zellij", "attach", "--create", name)


def in_zellij() -> bool:
    """True when running inside a zellij session ($ZELLIJ is set)."""
    return bool(os.environ.get("ZELLIJ"))


# --- cache format (pure) -----------------------------------------------------


def zellij_cache_root(home: Path, platform: str) -> Path:
    """Where zellij keeps its caches for this OS (not guaranteed to exist)."""
    if platform == "darwin":
        return home / "Library" / "Caches" / "org.Zellij-Contributors.Zellij"
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else home / ".cache"
    return base / "zellij"


def _balanced(text: str, brace_at: int) -> str:
    """Inner text of the ``{...}`` block whose opening brace is at *brace_at*."""
    depth = 0
    for i in range(brace_at, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[brace_at + 1 : i]
    return text[brace_at + 1 :]


def _section(text: str, name: str) -> str | None:
    """The inner text of a top-level ``name { ... }`` block, or None."""
    m = re.search(rf"\b{name}\s*\{{", text)
    return _balanced(text, m.end() - 1) if m else None


def parse_pane_titles(metadata: str) -> list[str]:
    """Titles of the real (non-plugin, non-suppressed, live) terminal panes.

    Plugin panes are zellij's own tab-bar/status-bar chrome; suppressed/exited
    panes aren't what you'd call "running", so all three are filtered out.
    """
    panes = _section(metadata, "panes")
    if panes is None:
        return []
    titles: list[str] = []
    for m in re.finditer(r"\bpane\s*\{", panes):
        block = _balanced(panes, m.end() - 1)
        if _PLUGIN.search(block) or _SUPPRESSED.search(block) or _EXITED.search(block):
            continue
        title = _TITLE.search(block)
        if title and title.group(1).strip():
            titles.append(title.group(1).strip())
    return titles


# --- the seam ----------------------------------------------------------------


class Zellij:
    """Talk to zellij — commands and cache — over the ProcessRunner port.

    One instance is built from the AppContext (`Zellij(ctx.runner, home=ctx.home)`)
    and handed the host paths so callers never touch the binary name, command
    flags, or cache layout directly.
    """

    def __init__(self, runner: ProcessRunner, *, home: Path, platform: str = sys.platform) -> None:
        self._runner = runner
        self._home = home
        self._cache_root = zellij_cache_root(home, platform)

    # --- commands ---

    def list_sessions(self) -> list[Session]:
        """Running/exited sessions, or raise SessionError on a real failure."""
        result = self._runner.run(("zellij", "list-sessions", "--no-formatting"))
        combined = result.stdout + result.stderr
        if _EMPTY_MARKER not in combined and not result.ok:
            raise SessionError(result.stderr.strip() or "zellij list-sessions failed")
        return parse_sessions(result.stdout)

    def kill_session(self, name: str) -> StepResult:
        """Kill a running session."""
        result = self._runner.run(("zellij", "kill-session", name))
        if result.ok:
            return StepResult(level="success", message=f"Killed session {name}")
        return StepResult(level="error", message=f"Could not kill session {name}")

    def delete_session(self, name: str) -> StepResult:
        """Delete an exited session's serialized state (`zellij delete-session`).

        Valid only for exited (resurrectable) sessions; a running one must be killed.
        """
        result = self._runner.run(("zellij", "delete-session", name))
        if result.ok:
            return StepResult(level="success", message=f"Deleted session {name}")
        return StepResult(level="error", message=f"Could not delete session {name}")

    def prune(self, names: Sequence[str]) -> list[StepResult]:
        """Delete each named (exited) session, returning a StepResult per deletion."""
        return [self.delete_session(name) for name in names]

    def attached_client_count(self) -> int | None:
        """Clients attached to the *current* session, or None if not inside one.

        `zellij action list-clients` (0.44+) only works from within a session and
        reports that session's clients — one row per client, first column a numeric
        CLIENT_ID. We count digit-led rows so an unexpected format degrades to None
        rather than crashing the TUI. Off-session, zellij exits non-zero -> None.
        """
        result = self._runner.run(("zellij", "action", "list-clients"))
        if not result.ok:
            return None
        rows = [line.split() for line in result.stdout.splitlines() if line.split()]
        count = sum(1 for cols in rows if cols[0].isdigit())
        return count or None

    # --- attach / layout (pure builders, bound to this host) ---

    def attach_command(
        self, name: str, *, exists: bool = False, layout: str | None = None
    ) -> tuple[str, ...]:
        """The zellij command to reach `name` (see module `attach_command`)."""
        return attach_command(name, exists=exists, layout=layout)

    def layout_for(self, name: str) -> str | None:
        """The curated layout deployed for `name`, or None."""
        return layout_name_for(self._home, name)

    # --- cache reads (best-effort; empty on any failure) ---

    def program_titles(self, name: str) -> list[str]:
        """Running terminal-pane titles for session *name*, or [] on any failure."""
        try:
            files = sorted(self._cache_root.glob(f"*/session_info/{name}/session-metadata.kdl"))
            if not files:
                return []
            metadata = files[-1].read_text()
        except OSError:
            return []
        return parse_pane_titles(metadata)
