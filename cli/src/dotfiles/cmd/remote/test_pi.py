from pathlib import Path

import pytest

from dotfiles.cmd.remote.pi import project_layout, resolve_project, session_name_for


def test_resolve_project_by_name(tmp_path: Path) -> None:
    project = tmp_path / "code" / "private" / "garden"
    project.mkdir(parents=True)

    assert resolve_project(tmp_path, "garden") == project


def test_resolve_project_accepts_absolute_path(tmp_path: Path) -> None:
    project = tmp_path / "elsewhere" / "garden"
    project.mkdir(parents=True)

    assert resolve_project(tmp_path, str(project)) == project


def test_resolve_project_rejects_ambiguous_name(tmp_path: Path) -> None:
    (tmp_path / "code" / "public" / "garden").mkdir(parents=True)
    (tmp_path / "code" / "private" / "garden").mkdir(parents=True)

    with pytest.raises(ValueError, match="ambiguous"):
        resolve_project(tmp_path, "garden")


def test_resolve_project_rejects_missing_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not found"):
        resolve_project(tmp_path, "missing")


def test_session_name_uses_project_basename() -> None:
    assert session_name_for(Path("/code/my-project")) == "pi-my-project"


def test_project_layout_starts_pi_and_leaves_a_shell_after_exit() -> None:
    layout = project_layout(Path('/code/project with "quotes"'), "pi-project")

    assert 'tab name="pi-project"' in layout
    assert 'cwd="/code/project with \\"quotes\\""' in layout
    assert 'args "-lc" "pi --continue; exec /bin/zsh -l"' in layout
