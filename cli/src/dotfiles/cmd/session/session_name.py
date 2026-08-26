"""Validation of zellij session names — one place that owns what's allowed.

The single rule today: a name must be non-empty and contain no whitespace.
"""

_ERROR = "Session name cannot contain spaces"


def is_valid(name: str) -> bool:
    """True if *name* is usable as a zellij session name (non-empty, no spaces)."""
    return bool(name) and not any(c.isspace() for c in name)


def error(name: str) -> str | None:
    """Why *name* is invalid, or None when its characters are acceptable.

    Reports character problems only; an empty name yields None because a blank
    field has nothing to complain about yet. Callers that must reject empty
    (e.g. a submit gate) use `is_valid` instead.
    """
    return _ERROR if any(c.isspace() for c in name) else None


def clean(name: str) -> str:
    """Drop whitespace characters, leaving a valid name."""
    return "".join(c for c in name if not c.isspace())
