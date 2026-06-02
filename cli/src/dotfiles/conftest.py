"""Shared pytest fixtures for the dotfiles-cli test suite."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def home(tmp_path: Path) -> Path:
    """A fresh, empty fake home directory under tmp_path.

    Replaces the six identical per-file ``home`` fixtures in the agent_setup
    tests. The per-agent ``dotfiles`` fixtures stay local — they each write a
    agent-specific source tree.
    """
    h = tmp_path / "home"
    h.mkdir()
    return h
