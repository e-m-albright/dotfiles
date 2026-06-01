"""Tests for the `dotfiles scaffold` Typer command.

These assert orchestration + arg handling; heavy per-module logic is covered in
test_scaffold_*.py.  All filesystem effects target tmp_path; git/lefthook calls
go through a FakeProcessRunner.  No real files are touched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dotfiles.cli.main import app
from tests.fakes import FakeProcessRunner, make_fake_context

runner = CliRunner()

# Rule paths a python scaffold expects to find under dotfiles/.ai/rules/.
_PY_RULES = [
    "languages/python.mdc",
    "tooling/stack-python.mdc",
    "tooling/services.mdc",
    "process/shell-automation.mdc",
]

_REGISTRY = {
    "tools": {
        "cursor": {
            "rulesDir": ".cursor/rules",
            "suffix": ".mdc",
            "strategy": "symlink",
            "symlinkPrefix": "../../",
            "rootFile": None,
        },
        "copilot": {
            "rulesDir": ".github/instructions",
            "suffix": ".instructions.md",
            "strategy": "symlink",
            "symlinkPrefix": "../../",
            "rootFile": None,
        },
        "codex": {
            "rulesDir": None,
            "suffix": None,
            "strategy": "symlink",
            "symlinkPrefix": None,
            "rootFile": "CODEX.md",
        },
    }
}


def _make_dotfiles(tmp_path: Path) -> Path:
    """Build a fake dotfiles source tree with rules + registry."""
    d = tmp_path / "dotfiles"
    rules = d / ".ai" / "rules"
    for rel in _PY_RULES:
        f = rules / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"# {rel}\nbody\n")
    registry = d / "agents" / "shared" / "tool-targets.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps(_REGISTRY))
    return d


def _ctx(tmp_path: Path, runner_fake: FakeProcessRunner | None = None):
    return make_fake_context(
        runner=runner_fake or FakeProcessRunner(),
        dotfiles_dir=_make_dotfiles(tmp_path),
    )


def test_help_shows_flags() -> None:
    result = runner.invoke(app, ["scaffold", "--help"])
    assert result.exit_code == 0
    for flag in (
        "--force",
        "--tools",
        "--with-audit-pipeline",
        "--with-baselines",
        "--with-code-health",
        "--with-agent-rules-sync",
    ):
        assert flag in result.output


def test_scaffolds_python_project(tmp_path: Path) -> None:
    """python project → .ai/rules/*.mdc w/ headers, AGENTS.md, artifacts, symlinks."""
    project = tmp_path / "proj"
    ctx = _ctx(tmp_path)

    result = runner.invoke(app, ["scaffold", "python", str(project)], obj=ctx)
    assert result.exit_code == 0, result.output

    rules = project / ".ai" / "rules"
    assert (rules / "python.mdc").is_file()
    assert (rules / "services.mdc").is_file()
    # Manifest header with today's date is prepended.
    assert (rules / "python.mdc").read_text().startswith("<!-- source: dotfiles/.ai/rules/")
    # AGENTS.md generated.
    assert (project / "AGENTS.md").is_file()
    # Artifacts tree.
    assert (project / ".ai" / "artifacts" / "decisions").is_dir()
    # Cursor symlinks (default tool).
    assert (project / ".cursor" / "rules" / "python.mdc").is_symlink()


def test_default_app_type_resolves(tmp_path: Path) -> None:
    """`scaffold python <path>` → fastapi default (header line shows it)."""
    project = tmp_path / "proj"
    ctx = _ctx(tmp_path)
    result = runner.invoke(app, ["scaffold", "python", str(project)], obj=ctx)
    assert "python/fastapi" in result.output


def test_known_app_type_positional(tmp_path: Path) -> None:
    """`scaffold python cli <path>` → app-type=cli, 3rd arg is the path."""
    project = tmp_path / "myproj"
    ctx = _ctx(tmp_path)
    result = runner.invoke(app, ["scaffold", "python", "cli", str(project)], obj=ctx)
    assert result.exit_code == 0, result.output
    assert "python/cli" in result.output
    assert (project / "AGENTS.md").is_file()


def test_app_type_without_path_errors(tmp_path: Path) -> None:
    """`scaffold python cli` (no path) → BadParameter about missing project path."""
    ctx = _ctx(tmp_path)
    result = runner.invoke(app, ["scaffold", "python", "cli"], obj=ctx)
    assert result.exit_code != 0
    assert "project path" in result.output.lower()


def test_unknown_recipe_errors(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    result = runner.invoke(app, ["scaffold", "elixir", str(tmp_path / "p")], obj=ctx)
    assert result.exit_code == 1
    assert "Unknown recipe" in result.output


def test_tools_all_uses_registry(tmp_path: Path) -> None:
    """`--tools all` → copilot symlinks created too (from the registry)."""
    project = tmp_path / "proj"
    ctx = _ctx(tmp_path)
    result = runner.invoke(app, ["scaffold", "python", str(project), "--tools", "all"], obj=ctx)
    assert result.exit_code == 0, result.output
    # copilot uses .github/instructions with .instructions.md suffix
    assert (project / ".github" / "instructions" / "python.instructions.md").is_symlink()
    # codex root symlink created
    assert (project / "CODEX.md").is_symlink()


def test_force_overwrites_rules(tmp_path: Path) -> None:
    """--force re-copies rules (overwriting a customized file)."""
    project = tmp_path / "proj"
    ctx = _ctx(tmp_path)
    # First scaffold.
    runner.invoke(app, ["scaffold", "python", str(project)], obj=ctx)
    customized = project / ".ai" / "rules" / "python.mdc"
    customized.write_text("CUSTOM\n")
    # Force re-scaffold over the existing project.
    result = runner.invoke(app, ["scaffold", "python", str(project), "--force"], obj=ctx)
    assert result.exit_code == 0, result.output
    # The customized content is replaced by the source rule + manifest header.
    assert "CUSTOM" not in customized.read_text()
    assert customized.read_text().startswith("<!-- source:")


def test_missing_git_fast_fails_for_new_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A new project with git unavailable exits 1 with a clear message, no git init."""
    project = tmp_path / "proj"
    fake = FakeProcessRunner()
    ctx = make_fake_context(runner=fake, dotfiles_dir=_make_dotfiles(tmp_path))

    # Fake `which`: git is missing, everything else present.
    def _which(cmd: str) -> str | None:
        return None if cmd == "git" else f"/usr/bin/{cmd}"

    monkeypatch.setattr("dotfiles.cli.scaffold.shutil.which", _which)

    result = runner.invoke(app, ["scaffold", "python", str(project)], obj=ctx)
    assert result.exit_code == 1
    assert "git is required" in result.output.lower()
    # No git command was ever attempted.
    assert not any(c[0] == "git" for c in fake.calls)


def test_git_init_invoked_for_new_project(tmp_path: Path) -> None:
    """A new project triggers git init + add + commit through the runner."""
    project = tmp_path / "proj"
    fake = FakeProcessRunner()
    ctx = make_fake_context(runner=fake, dotfiles_dir=_make_dotfiles(tmp_path))
    result = runner.invoke(app, ["scaffold", "python", str(project)], obj=ctx)
    assert result.exit_code == 0, result.output
    git_calls = [c for c in fake.calls if c[0] == "git"]
    assert any("init" in c for c in git_calls)
    assert any("commit" in c for c in git_calls)
