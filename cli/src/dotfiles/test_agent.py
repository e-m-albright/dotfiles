"""Tests for the vendor registry — the single source of truth for agent stances."""

from __future__ import annotations

from pathlib import Path

import pytest

from dotfiles.agent import (
    AGENTS,
    OVERVIEW_AGENTS,
    SURFACES,
    VENDOR_BY_NAME,
    VENDORS,
    Agent,
    Deploy,
    Local,
    Native,
    SurfaceName,
    surface_path,
)

HOME = Path("/home/test")


def test_surface_path_resolves_declared_surface() -> None:
    assert surface_path(HOME, "claude", "rules") == HOME / ".claude/CLAUDE.md"
    assert surface_path(HOME, "codex", "mcp") == HOME / ".codex/config.toml"


def test_surface_path_raises_for_undeclared_surface() -> None:
    # Hermes is a skills-only vendor: it declares no settings deploy.
    with pytest.raises(KeyError, match="hermes"):
        surface_path(HOME, "hermes", "settings")


def test_surface_path_raises_for_repo_rooted_deploy() -> None:
    # Cursor rules live in the repo, not under home — resolving via home would lie.
    with pytest.raises(KeyError, match="cursor"):
        surface_path(HOME, "cursor", "rules")


def test_registry_indexes_agree() -> None:
    assert set(VENDOR_BY_NAME) == set(AGENTS)
    assert tuple(v.name for v in VENDORS) == AGENTS
    assert set(OVERVIEW_AGENTS) <= set(AGENTS)


def test_every_stance_is_a_known_kind() -> None:
    for v in VENDORS:
        for surface in SURFACES:
            stance = v.surfaces.stance(surface)
            assert stance is None or isinstance(stance, (Deploy, Native, Local))


def test_local_stances_carry_a_reason() -> None:
    """A Local without a why is an unexplained n/a — exactly the lie we removed."""
    for v in VENDORS:
        for surface in SURFACES:
            stance = v.surfaces.stance(surface)
            if isinstance(stance, Local):
                assert stance.why, f"{v.name}/{surface} Local stance has no reason"


@pytest.mark.parametrize(
    ("vendor", "surface"),
    [
        # The surfaces the doctor probe resolves through the registry.
        ("claude", "rules"),
        ("claude", "settings"),
        ("claude", "mcp"),
        ("codex", "rules"),
        ("codex", "hooks"),
        ("codex", "mcp"),
        # The settings surfaces the overview probe resolves through the registry.
        ("codex", "settings"),
        ("cursor", "settings"),
        ("gemini", "settings"),
    ],
)
def test_probed_surfaces_are_declared(vendor: Agent, surface: SurfaceName) -> None:
    """Drift guard: every surface a probe reads must exist in the registry.

    If a vendor's path moves or a surface is dropped, ``surface_path`` raises and
    this fails loudly — instead of doctor/overview silently checking nothing.
    """
    assert surface_path(HOME, vendor, surface).is_absolute()
