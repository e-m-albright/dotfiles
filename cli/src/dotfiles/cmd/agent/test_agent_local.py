"""Tests for `agent local` (cli/src/dotfiles/cmd/agent/local.py).

All tests use tmp_path for the scaffold (dotfiles_dir) and a fake target repo.
The deployed engine is never actually run — FakeProcessRunner records the call.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dotfiles.cmd.agent.local import CANONICAL_VENDORS, align_repo
from dotfiles.testing.fakes import FakeProcessRunner, write_tree

SYNC_ENGINE = "#!/usr/bin/env bash\necho sync\n"
LEFTHOOK_FRAGMENT = "pre-commit:\n  commands:\n    agent-rules-synced:\n      run: ./x.sh --check\n"


@pytest.fixture
def dotfiles(tmp_path: Path) -> Path:
    d = tmp_path / "dotfiles"
    write_tree(
        d,
        {
            "ai/rules-sync/scripts/sync-agent-rules.sh": SYNC_ENGINE,
            "ai/rules-sync/lefthook.agent-rules.yml": LEFTHOOK_FRAGMENT,
        },
    )
    return d


@pytest.fixture
def target(tmp_path: Path) -> Path:
    t = tmp_path / "project"
    write_tree(t, {"AGENTS.md": "# Project\n", ".git/HEAD": "ref: refs/heads/main\n"})
    return t


def _all() -> set[str]:
    return set(CANONICAL_VENDORS)


def _run(dotfiles: Path, target: Path, **kw: object) -> list:
    runner = kw.pop("runner", FakeProcessRunner())
    vendors = kw.pop("vendors", _all())
    return align_repo(runner=runner, dotfiles_dir=dotfiles, target=target, vendors=vendors, **kw)  # type: ignore[arg-type]


def _engine_call(runner: FakeProcessRunner) -> tuple[str, ...]:
    return next(c for c in runner.calls if "sync-agent-rules.sh" in c[0])


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------


class TestGuard:
    def test_non_git_repo_errors(self, dotfiles: Path, tmp_path: Path) -> None:
        plain = tmp_path / "plain"
        write_tree(plain, {"AGENTS.md": "# x\n"})
        results = align_repo(
            runner=FakeProcessRunner(), dotfiles_dir=dotfiles, target=plain, vendors=_all()
        )
        assert results[0].level == "error"
        assert "git repository" in results[0].message

    def test_missing_agents_md_errors(self, dotfiles: Path, tmp_path: Path) -> None:
        t = tmp_path / "noagents"
        write_tree(t, {".git/HEAD": "ref: refs/heads/main\n"})
        results = align_repo(
            runner=FakeProcessRunner(), dotfiles_dir=dotfiles, target=t, vendors=_all()
        )
        assert any(r.level == "error" and "AGENTS.md" in r.message for r in results)


# ---------------------------------------------------------------------------
# Apply (default)
# ---------------------------------------------------------------------------


class TestApply:
    def test_deploys_engine(self, dotfiles: Path, target: Path) -> None:
        _run(dotfiles, target)
        assert (target / "scripts" / "sync-agent-rules.sh").is_file()

    def test_engine_is_executable(self, dotfiles: Path, target: Path) -> None:
        _run(dotfiles, target)
        assert (target / "scripts" / "sync-agent-rules.sh").stat().st_mode & 0o111

    def test_deploys_lefthook_fragment(self, dotfiles: Path, target: Path) -> None:
        _run(dotfiles, target)
        assert (target / "lefthook.agent-rules.yml").is_file()

    def test_adds_markers_to_agents_md(self, dotfiles: Path, target: Path) -> None:
        _run(dotfiles, target)
        assert "BEGIN: project rules" in (target / "AGENTS.md").read_text()

    def test_runs_engine(self, dotfiles: Path, target: Path) -> None:
        runner = FakeProcessRunner()
        _run(dotfiles, target, runner=runner)
        assert any("sync-agent-rules.sh" in c[0] for c in runner.calls)

    def test_all_steps_ok(self, dotfiles: Path, target: Path) -> None:
        assert all(r.ok for r in _run(dotfiles, target))

    def test_idempotent(self, dotfiles: Path, target: Path) -> None:
        _run(dotfiles, target)
        assert all(r.ok for r in _run(dotfiles, target))


# ---------------------------------------------------------------------------
# Check (read-only)
# ---------------------------------------------------------------------------


class TestCheck:
    def test_check_does_not_deploy(self, dotfiles: Path, target: Path) -> None:
        _run(dotfiles, target, check=True)
        assert not (target / "scripts" / "sync-agent-rules.sh").exists()

    def test_check_does_not_modify_agents_md(self, dotfiles: Path, target: Path) -> None:
        before = (target / "AGENTS.md").read_text()
        _run(dotfiles, target, check=True)
        assert (target / "AGENTS.md").read_text() == before

    def test_check_reports_drift(self, dotfiles: Path, target: Path) -> None:
        assert any(r.level == "warn" for r in _run(dotfiles, target, check=True))


# ---------------------------------------------------------------------------
# Vendor scope
# ---------------------------------------------------------------------------


class TestVendorScope:
    def test_cursor_excluded_passes_no_cursor(self, dotfiles: Path, target: Path) -> None:
        runner = FakeProcessRunner()
        _run(dotfiles, target, runner=runner, vendors={"claude", "codex"})
        assert "--no-cursor" in _engine_call(runner)

    def test_cursor_included_omits_flag(self, dotfiles: Path, target: Path) -> None:
        runner = FakeProcessRunner()
        _run(dotfiles, target, runner=runner, vendors={"cursor", "claude"})
        assert "--no-cursor" not in _engine_call(runner)

    def test_dead_symlink_pruned_for_in_scope_vendor(self, dotfiles: Path, target: Path) -> None:
        link = target / ".claude" / "rules"
        link.parent.mkdir(parents=True)
        link.symlink_to(target / ".ai" / "rules")
        _run(dotfiles, target, vendors={"claude"})
        assert not link.is_symlink()

    def test_dead_symlink_kept_for_out_of_scope_vendor(self, dotfiles: Path, target: Path) -> None:
        link = target / ".gemini" / "rules"
        link.parent.mkdir(parents=True)
        link.symlink_to(target / ".ai" / "rules")
        _run(dotfiles, target, vendors={"claude"})  # gemini out of scope
        assert link.is_symlink()

    def test_keep_dead_symlinks_flag_preserves(self, dotfiles: Path, target: Path) -> None:
        link = target / ".claude" / "rules"
        link.parent.mkdir(parents=True)
        link.symlink_to(target / ".ai" / "rules")
        _run(dotfiles, target, vendors={"claude"}, keep_dead_symlinks=True)
        assert link.is_symlink()
