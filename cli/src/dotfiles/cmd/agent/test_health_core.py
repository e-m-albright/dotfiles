"""Tests for the `dotfiles agent health` bootstrap service."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from dotfiles.cmd.agent.health import (
    SUPPRESSION_PATTERNS,
    HealthError,
    HealthService,
    git_root,
)
from dotfiles.testing.fakes import FakeProcessRunner

_TODAY = date(2026, 6, 7)
_CARD = {
    "loc": 1234,
    "since": "6 months ago",
    "suppressions": {"type-ignore": 3, "todo": 7},
    "hotspots": [{"file": "a.py", "score": 100, "churn": 10, "loc": 10}],
}


def _svc(runner: FakeProcessRunner, scripts: Path) -> HealthService:
    return HealthService(runner=runner, scripts_dir=scripts)


def _scripted_runner(scripts: Path, card: dict | None = None) -> FakeProcessRunner:
    runner = FakeProcessRunner()
    runner.script(
        (str(scripts / "scorecard.sh"), "--json"),
        stdout=json.dumps(_CARD if card is None else card),
    )
    return runner


def test_bootstrap_seeds_baselines_and_findings(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    runner = _scripted_runner(scripts)
    target = tmp_path / "repo"
    target.mkdir()

    result = _svc(runner, scripts).bootstrap(
        target=target,
        scope="cli",
        files_glob="src/**/*.py",
        run_from="cli/",
        today=_TODAY,
    )

    assert result.created is True
    assert result.total_suppressions == 10
    baselines = target / "docs" / "health" / "cli" / "baselines.json"
    doc = json.loads(baselines.read_text())
    assert doc["scope"] == "cli"
    assert doc["files_glob"] == "src/**/*.py"
    assert doc["run_from"] == "cli/"
    assert doc["loc_nontest"] == 1234
    assert doc["updated"] == "2026-06-07"
    assert set(doc["suppression_patterns"]) == set(SUPPRESSION_PATTERNS)
    # findings ledger seeded with the standard sections.
    findings = (target / "docs" / "health" / "cli" / "findings.md").read_text()
    assert "Code-health findings" in findings
    assert "Open backlog" in findings


def test_bootstrap_runs_ratchet_update_from_run_from(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    runner = _scripted_runner(scripts)
    target = tmp_path / "repo"
    target.mkdir()

    _svc(runner, scripts).bootstrap(
        target=target, scope="cli", files_glob="src/**/*.py", run_from="cli/", today=_TODAY
    )

    baselines = target / "docs" / "health" / "cli" / "baselines.json"
    ratchet_cmd = (str(scripts / "ratchet-check.sh"), str(baselines), "--update")
    assert ratchet_cmd in runner.calls
    idx = runner.calls.index(ratchet_cmd)
    assert runner.cwds[idx] == target / "cli/"
    # scorecard ran against the repo root itself.
    sc_idx = runner.calls.index((str(scripts / "scorecard.sh"), "--json"))
    assert runner.cwds[sc_idx] == target


def test_bootstrap_keeps_existing_baselines(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    runner = _scripted_runner(scripts)
    target = tmp_path / "repo"
    target.mkdir()
    svc = _svc(runner, scripts)
    svc.bootstrap(target=target, scope="repo", files_glob="**/*", run_from=".", today=_TODAY)

    # Simulate the ratchet having lowered a ceiling; a second run must not clobber it.
    baselines = target / "docs" / "health" / "repo" / "baselines.json"
    doc = json.loads(baselines.read_text())
    doc["suppressions"]["todo"] = 5
    baselines.write_text(json.dumps(doc))

    result = svc.bootstrap(
        target=target, scope="repo", files_glob="**/*", run_from=".", today=_TODAY
    )
    assert result.created is False
    assert json.loads(baselines.read_text())["suppressions"]["todo"] == 5


def test_force_reseeds(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    runner = _scripted_runner(scripts)
    target = tmp_path / "repo"
    target.mkdir()
    svc = _svc(runner, scripts)
    svc.bootstrap(target=target, scope="repo", files_glob="**/*", run_from=".", today=_TODAY)
    result = svc.bootstrap(
        target=target, scope="repo", files_glob="**/*", run_from=".", today=_TODAY, force=True
    )
    assert result.created is True


def test_scorecard_failure_raises(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    runner = FakeProcessRunner()
    runner.script((str(scripts / "scorecard.sh"), "--json"), exit_code=1, stderr="boom")
    with pytest.raises(HealthError, match="boom"):
        _svc(runner, scripts).bootstrap(
            target=tmp_path, scope="r", files_glob="**/*", run_from=".", today=_TODAY
        )


def test_invalid_json_raises(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    runner = FakeProcessRunner()
    runner.script((str(scripts / "scorecard.sh"), "--json"), stdout="not json")
    with pytest.raises(HealthError, match="invalid JSON"):
        _svc(runner, scripts).bootstrap(
            target=tmp_path, scope="r", files_glob="**/*", run_from=".", today=_TODAY
        )


def test_ratchet_failure_raises(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    runner = _scripted_runner(scripts)
    target = tmp_path / "repo"
    target.mkdir()
    baselines = target / "docs" / "health" / "r" / "baselines.json"
    runner.script(
        (str(scripts / "ratchet-check.sh"), str(baselines), "--update"),
        exit_code=2,
        stderr="no baseline",
    )
    with pytest.raises(HealthError, match="no baseline"):
        _svc(runner, scripts).bootstrap(
            target=target, scope="r", files_glob="**/*", run_from=".", today=_TODAY
        )


def test_git_root_resolves_toplevel() -> None:
    runner = FakeProcessRunner()
    runner.script(("git", "rev-parse", "--show-toplevel"), stdout="/x/repo\n")
    assert git_root(runner) == Path("/x/repo")


def test_git_root_outside_repo_raises() -> None:
    runner = FakeProcessRunner()
    runner.script(("git", "rev-parse", "--show-toplevel"), exit_code=128)
    with pytest.raises(HealthError, match="not inside a git repo"):
        git_root(runner)
