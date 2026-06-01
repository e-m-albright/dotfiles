"""Session hand-off: attach to (or switch into) a zellij session from the TUI."""

from __future__ import annotations

import os


def zellij_handoff_command(name: str, *, in_zellij: bool) -> tuple[str, ...]:
    """Return the command to reach session `name`.

    Inside an existing zellij ($ZELLIJ set) we switch sessions in place; otherwise
    we attach (creating if absent). Kept pure so it is unit-testable without a TTY.
    """
    if in_zellij:
        return ("zellij", "action", "switch-session", name)
    return ("zellij", "attach", "--create", name)


def in_zellij() -> bool:
    return bool(os.environ.get("ZELLIJ"))
