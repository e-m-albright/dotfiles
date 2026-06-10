"""Tests for RepoAuditService — Canon conformance over a tmp repo."""

from __future__ import annotations

from pathlib import Path

from dotfiles.cmd.repo.service import RepoAuditService


def _audit(repo: Path):
    return RepoAuditService(repo_path=repo).audit()


def _checks(repo: Path) -> dict[str, str]:
    return {c.name: c.status for c in _audit(repo).checks}


def _conformant_python_repo(repo: Path) -> None:
    """Seed a repo that satisfies every required Canon check."""
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "justfile").write_text("default:\n    @just --list\nratchet:\n    converge\n")
    (repo / "lefthook.yml").write_text("pre-commit:\n  commands: {}\n")
    (repo / "README.md").write_text("# repo")
    (repo / "AGENTS.md").write_text("rules")
    (repo / ".gitignore").write_text("*.pyc")
    (repo / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n")
    (repo / "uv.lock").write_text("# lock")
    workflows = repo / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: ci")


def test_conformant_repo_grades_a_with_no_failures(tmp_path: Path) -> None:
    repo = tmp_path / "good"
    _conformant_python_repo(repo)
    audit = _audit(repo)
    assert audit.grade == "A"
    assert audit.failures == 0
    assert audit.stack == "python"


def test_bare_repo_fails_required_gates(tmp_path: Path) -> None:
    repo = tmp_path / "bare"
    repo.mkdir()
    checks = _checks(repo)
    assert checks["justfile"] == "fail"
    assert checks["lefthook"] == "fail"
    assert checks["CI"] == "fail"
    assert checks["AGENTS.md"] == "fail"
    assert _audit(repo).grade == "F"


def test_ruff_in_pyproject_counts_as_linter(tmp_path: Path) -> None:
    repo = tmp_path / "py"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[tool.ruff]\n")
    assert _checks(repo)["linter"] == "pass"


def test_python_without_ruff_fails_linter(tmp_path: Path) -> None:
    repo = tmp_path / "py2"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    assert _checks(repo)["linter"] == "fail"


def test_unknown_stack_marks_linter_na(tmp_path: Path) -> None:
    repo = tmp_path / "bash"
    repo.mkdir()
    (repo / "script.sh").write_text("echo hi")
    assert _checks(repo)["linter"] == "na"


def test_missing_lockfile_is_a_warning_not_failure(tmp_path: Path) -> None:
    repo = tmp_path / "nolock"
    repo.mkdir()
    (repo / "Cargo.toml").write_text("[package]\nname = 'x'\n")
    checks = _checks(repo)
    assert checks["lockfile"] == "warn"  # recommended, not required
    assert _audit(repo).failures > 0  # other required gates still fail


def test_na_checks_excluded_from_grade(tmp_path: Path) -> None:
    repo = tmp_path / "good2"
    _conformant_python_repo(repo)
    audit = _audit(repo)
    assert all(c.status != "na" for c in audit.required)
