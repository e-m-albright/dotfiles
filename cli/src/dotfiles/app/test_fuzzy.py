"""Tests for the conservative fuzzy command resolver."""

from __future__ import annotations

import pytest

from dotfiles.app.fuzzy import _within_one_edit, closest_command

_SESSION_COMMANDS = ["list", "attach", "new", "kill", "prune"]


@pytest.mark.parametrize("typed", ["session", "sesion", "sessioo"])  # exact-ish / typo
def test_singular_plural_toggle_and_typos(typed: str) -> None:
    assert closest_command("sessions", ["session", "brew", "doctor"]) == "session"
    assert closest_command(typed, ["session", "brew", "doctor"]) == "session"


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("attch", "attach"),  # one-char deletion
        ("attachh", "attach"),  # one-char insertion
        ("pru", "prune"),  # unique prefix
    ],
)
def test_resolves_unambiguous_near_miss(typed: str, expected: str) -> None:
    assert closest_command(typed, _SESSION_COMMANDS) == expected


@pytest.mark.parametrize("typed", ["", "zzzplugh", "atatch"])
def test_conservative_when_ambiguous_or_distant(typed: str) -> None:
    # Empty and distant commands do not resolve; a transposition is two edits.
    assert closest_command(typed, _SESSION_COMMANDS) is None


@pytest.mark.parametrize(
    ("a", "b", "within"),
    [
        ("agent", "agent", True),  # equal
        ("agnt", "agent", True),  # one insertion
        ("agents", "agent", True),  # one deletion
        ("agemt", "agent", True),  # one substitution
        ("agnet", "agent", False),  # transposition = two substitutions
        ("xy", "agent", False),  # length gap > 1
    ],
)
def test_within_one_edit(a: str, b: str, within: bool) -> None:
    assert _within_one_edit(a, b) is within
