"""Validation of zellij session names — one place that owns what's allowed.

A session name must be non-empty and free of every character class listed in
`_INVALID_CLASSES`. Each class pairs a predicate (which characters it matches)
with the human label used in error messages, so adding a rule — say, forbidding
slashes — means appending one entry here: `is_valid`, `error`, and `clean` all
derive from this single table rather than re-encoding the rule three times.
"""

from collections.abc import Callable

# (matches an invalid character, human label) — the single source of truth for
# what a session name may not contain.
_INVALID_CLASSES: tuple[tuple[Callable[[str], bool], str], ...] = ((str.isspace, "spaces"),)


def _invalid_labels(name: str) -> tuple[str, ...]:
    """Labels of the invalid character classes *name* trips, in table order."""
    return tuple(label for matches, label in _INVALID_CLASSES if any(matches(c) for c in name))


def _is_invalid_char(char: str) -> bool:
    return any(matches(char) for matches, _ in _INVALID_CLASSES)


def is_valid(name: str) -> bool:
    """True if *name* is usable as a zellij session name (non-empty, no bad chars)."""
    return bool(name) and not _invalid_labels(name)


def error(name: str) -> str | None:
    """Why *name* is invalid, or None when its characters are acceptable.

    Reports character problems only; an empty name yields None because a blank
    field has nothing to complain about yet. Callers that must reject empty
    (e.g. a submit gate) use `is_valid` instead.
    """
    labels = _invalid_labels(name)
    if not labels:
        return None
    return f"Session name cannot contain {', '.join(labels)}"


def clean(name: str) -> str:
    """Drop every character belonging to an invalid class, leaving a valid name."""
    return "".join(char for char in name if not _is_invalid_char(char))
