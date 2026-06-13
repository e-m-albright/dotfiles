"""Drift gate for the canonical deny-command vocabulary.

``ai/agents/shared/deny-commands.yaml`` is the single source of truth for the
universal 'hard stop' commands. Each entry names, per surface, the exact string
that must appear in that surface's committed config. This test fails the moment
a canonical string is missing from its vendor file, turning silent drift into a
caught error (engineering-philosophy principle #3, same pattern as
test_command_tree.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dotfiles.cmd.agent.deny_commands import (
    SURFACE_FILES,
    deny_strings_in_config,
    load_deny_entries,
    strings_for_surface,
)

_REPO = Path(__file__).resolve().parents[5]


def _surface_cases() -> list[tuple[str, str, str]]:
    """(surface, entry_id, string) for every per-surface deny string."""
    cases: list[tuple[str, str, str]] = []
    for entry in load_deny_entries(_REPO):
        for surface, string in entry.surfaces.items():
            cases.append((surface, entry.id, string))
    return cases


def test_registry_is_nonempty() -> None:
    entries = load_deny_entries(_REPO)
    assert len(entries) >= 10, "deny-commands.yaml looks suspiciously small"


def test_every_surface_has_a_known_file() -> None:
    for entry in load_deny_entries(_REPO):
        for surface in entry.surfaces:
            assert surface in SURFACE_FILES, f"unknown surface {surface!r} in entry {entry.id}"


@pytest.mark.parametrize(("surface", "entry_id", "string"), _surface_cases())
def test_canonical_string_present_in_vendor_file(surface: str, entry_id: str, string: str) -> None:
    present = deny_strings_in_config(_REPO, surface)
    assert string in present, (
        f"deny-commands.yaml entry {entry_id!r} declares {surface} pattern {string!r}, "
        f"but it is missing from {SURFACE_FILES[surface]}. Add it there or update the registry."
    )


def test_claude_allow_and_deny_are_disjoint() -> None:
    """A command in both allow and deny is an ambiguous safety floor: deny wins at
    runtime, but the contradicting allow is noise that could mislead a maintainer
    or flip meaning if precedence ever changed. The two lists must not intersect.
    """
    import json

    perms = json.loads((_REPO / "ai" / "agents" / "claude" / "permissions.json").read_text())
    overlap = set(perms["allow"]) & set(perms["deny"])
    assert not overlap, f"these patterns are in BOTH allow and deny: {sorted(overlap)}"


def test_pi_policy_covers_all_pi_entries() -> None:
    """Pi is the locked-down floor — every pi-surface string must be in its policy."""
    pi_strings = set(strings_for_surface(_REPO, "pi"))
    present = deny_strings_in_config(_REPO, "pi")
    missing = sorted(pi_strings - present)
    assert not missing, f"Pi permission-policy.json missing canonical patterns: {missing}"
