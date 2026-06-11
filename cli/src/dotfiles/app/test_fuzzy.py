"""Tests for the conservative fuzzy command resolver."""

from __future__ import annotations

import pytest

from dotfiles.app.fuzzy import _within_one_edit, closest_command

_AGENT_COMMANDS = ["overview", "instructions", "catechism", "skills", "setup", "stats", "verify"]


@pytest.mark.parametrize("typed", ["agent", "agnt", "agemt"])  # exact-ish / typo
def test_singular_plural_toggle_and_typos(typed: str) -> None:
    # the canonical case the QOL is for: `dfs agents` should find `agent`.
    assert closest_command("agents", ["agent", "brew", "doctor"]) == "agent"
    assert closest_command(typed, ["agent", "brew", "doctor"]) == "agent"


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("overviw", "overview"),  # one-char deletion
        ("overvieww", "overview"),  # one-char insertion
        ("instru", "instructions"),  # unique prefix
    ],
)
def test_resolves_unambiguous_near_miss(typed: str, expected: str) -> None:
    assert closest_command(typed, _AGENT_COMMANDS) == expected


@pytest.mark.parametrize("typed", ["s", "", "zzzplugh", "verfiy"])
def test_conservative_when_ambiguous_or_distant(typed: str) -> None:
    # "s" → 3 candidates; "" → none; distant → none; "verfiy" → a transposition
    # (two edits), which we deliberately don't guess. None of these resolve.
    assert closest_command(typed, _AGENT_COMMANDS) is None


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
