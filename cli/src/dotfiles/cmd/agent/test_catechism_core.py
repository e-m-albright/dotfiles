"""Tests for the catechism doctrine backbone + scope-health reader."""

from __future__ import annotations

import json
from pathlib import Path

from dotfiles.cmd.agent.catechism import DOCTRINE, read_scope_health

_REPO = Path(__file__).resolve().parents[5]


def test_every_doctrine_doc_exists() -> None:
    # Drift gate: the doctrine index must point only at real curated docs.
    for layer in DOCTRINE:
        assert (_REPO / layer.doc).is_file(), f"missing doctrine doc: {layer.doc}"


def test_doctrine_is_ordered_outermost_first() -> None:
    names = [layer.name for layer in DOCTRINE]
    assert names[0] == "Canon"
    assert "Portfolio" in names


def test_read_scope_health_parses_baselines(tmp_path: Path) -> None:
    scope = tmp_path / "docs" / "health" / "cli"
    scope.mkdir(parents=True)
    (scope / "baselines.json").write_text(
        json.dumps(
            {
                "scope": "cli/src",
                "loc_nontest": 9010,
                "complexity": {"cognitive_max": 9, "functions_over_9": 2},
                "suppressions": {"cast": 35, "noqa": 0},
                "updated": "2026-06-07",
            }
        )
    )
    scopes = read_scope_health(tmp_path)
    assert len(scopes) == 1
    s = scopes[0]
    assert s.scope == "cli/src"
    assert s.loc == 9010
    assert s.complexity_over == 2
    assert s.suppressions["cast"] == 35


def test_read_scope_health_skips_dirs_without_baselines(tmp_path: Path) -> None:
    (tmp_path / "docs" / "health" / "cli").mkdir(parents=True)
    (tmp_path / "docs" / "health" / "ASSESSMENT.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "health" / "ASSESSMENT.md").write_text("# prose")
    assert read_scope_health(tmp_path) == []


def test_read_scope_health_empty_when_absent(tmp_path: Path) -> None:
    assert read_scope_health(tmp_path) == []


def test_real_repo_has_a_health_scope() -> None:
    scopes = read_scope_health(_REPO)
    assert any(s.loc > 0 for s in scopes), "expected at least the cli scope baseline"
