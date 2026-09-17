"""Password generation: the `openssl rand | tr | cut` one-liner, made a command."""

from __future__ import annotations

import secrets
import shutil
import string
from collections.abc import Callable

from dotfiles.adapters.ports import ProcessRunner

DEFAULT_LENGTH = 20

_ALPHABET = string.ascii_letters + string.digits
_CLASSES = (string.ascii_lowercase, string.ascii_uppercase, string.digits)


def copy_to_clipboard(
    runner: ProcessRunner,
    text: str,
    *,
    which: Callable[[str], str | None] = shutil.which,
) -> bool:
    """Copy text through macOS pbcopy, returning false when it is unavailable."""
    if which("pbcopy") is None:
        return False
    return runner.run(("pbcopy",), stdin=text).ok


def generate_password(length: int = DEFAULT_LENGTH) -> str:
    """Return a cryptographically random alphanumeric password of *length* chars.

    Rejection-samples until every character class (lower/upper/digit) appears,
    so the result survives "must contain a number" validators without biasing
    individual positions. Skipped when *length* < 3 makes that impossible.
    """
    while True:
        candidate = "".join(secrets.choice(_ALPHABET) for _ in range(length))
        if length < len(_CLASSES) or all(set(c) & set(candidate) for c in _CLASSES):
            return candidate
