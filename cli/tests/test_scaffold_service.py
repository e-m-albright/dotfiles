"""Direct unit tests for the extracted ScaffoldService / build_plan.

These exercise the disambiguation and abort-before-mutate logic without going
through Typer — the point of moving the orchestration out of the CLI layer.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dotfiles.core.scaffold.recipes import DEFAULT_APP_TYPES
from dotfiles.core.scaffold.service import (
    ScaffoldError,
    ScaffoldService,
    build_plan,
    disambiguate,
    gitignore_entries,
    resolve_tools_filter,
)
from tests.fakes import FakeProcessRunner


def _plan(tmp_path: Path):
    return build_plan(
        "python",
        str(tmp_path / "new"),
        None,
        force=False,
        tools="cursor",
        today="2026-01-01",
    )


def test_build_plan_rejects_unknown_recipe() -> None:
    with pytest.raises(ScaffoldError, match="Unknown recipe"):
        build_plan("elixir", "/tmp/p", None, force=False, tools="cursor", today="2026-01-01")


def test_build_plan_rejects_app_type_without_path() -> None:
    with pytest.raises(ScaffoldError, match="project path"):
        build_plan("python", "cli", None, force=False, tools="cursor", today="2026-01-01")


def test_build_plan_injects_today_and_marks_new(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    assert plan.today == "2026-01-01"  # core never reads the clock
    assert plan.is_new is True
    assert plan.app_type == DEFAULT_APP_TYPES["python"]


def test_disambiguate_known_app_type() -> None:
    assert disambiguate("python", "cli", "proj") == ("cli", "proj")


def test_resolve_tools_filter_prepends_cursor() -> None:
    assert resolve_tools_filter("all") == "all"
    assert resolve_tools_filter("cursor") == "cursor"
    assert resolve_tools_filter("copilot") == "cursor,copilot"


def test_gitignore_entries_includes_selected_rule_dirs() -> None:
    assert ".cursor/rules/" in gitignore_entries({}, "cursor")
    assert ".gemini/rules/" in gitignore_entries({}, "all")


def test_run_aborts_before_mutating_when_git_missing(tmp_path: Path) -> None:
    fake = FakeProcessRunner()
    service = ScaffoldService(runner=fake, dotfiles_dir=tmp_path, which=lambda _cmd: None)
    steps = service.run(_plan(tmp_path))
    assert any(s.level == "error" and "git is required" in s.message for s in steps)
    assert fake.calls == []  # no git/lefthook subprocess ran
    assert not (tmp_path / "new").exists()  # no filesystem changes
