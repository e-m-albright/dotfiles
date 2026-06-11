"""Tests for the vendor registry — the single source of truth for agent surfaces."""

from __future__ import annotations

from pathlib import Path

import pytest

from dotfiles.agent import (
    AGENTS,
    OVERVIEW_AGENTS,
    SURFACE_PATHS,
    VENDOR_BY_NAME,
    VENDORS,
    surface_path,
)

HOME = Path("/home/test")


def test_surface_path_resolves_declared_surface() -> None:
    assert surface_path(HOME, "claude", "instructions") == HOME / ".claude/CLAUDE.md"
    assert surface_path(HOME, "codex", "mcp") == HOME / ".codex/config.toml"


def test_surface_path_raises_for_undeclared_surface() -> None:
    # Hermes is a skills-only vendor: it declares no settings surface.
    with pytest.raises(KeyError, match="hermes"):
        surface_path(HOME, "hermes", "settings")


def test_registry_indexes_agree() -> None:
    assert set(VENDOR_BY_NAME) == set(AGENTS)
    assert tuple(v.name for v in VENDORS) == AGENTS
    assert set(OVERVIEW_AGENTS) <= set(AGENTS)


@pytest.mark.parametrize(
    ("vendor", "surface"),
    [
        # The surfaces the doctor probe resolves through the registry.
        ("claude", "instructions"),
        ("claude", "settings"),
        ("claude", "mcp"),
        ("codex", "instructions"),
        ("codex", "hooks"),
        ("codex", "mcp"),
        # The settings surfaces the overview probe resolves through the registry.
        ("codex", "settings"),
        ("cursor", "settings"),
        ("gemini", "settings"),
    ],
)
def test_probed_surfaces_are_declared(vendor: str, surface: str) -> None:
    """Drift guard: every surface a probe reads must exist in the registry.

    If a vendor's path moves or a surface is dropped, ``surface_path`` raises and
    this fails loudly — instead of doctor/overview silently checking nothing.
    """
    assert SURFACE_PATHS[surface][vendor] is not None
    assert surface_path(HOME, vendor, surface).is_absolute()
