from pathlib import Path

from dotfiles.cmd.agent.skill_prune import (
    external_skill_names,
    find_orphans,
    prune_orphans,
)
from dotfiles.testing.fakes import FakeProcessRunner, write_tree


def _git_history(dotfiles: Path, *paths: str) -> FakeProcessRunner:
    """A runner whose `git log --name-only` over *dotfiles* yields the given paths."""
    runner = FakeProcessRunner()
    runner.script(
        ("git", "-C", str(dotfiles), "log", "--all", "--pretty=format:", "--name-only"),
        stdout="\n".join(paths),
    )
    return runner


def _dotfiles(tmp_path: Path, canonical: list[str], external: str = "") -> Path:
    """A fake dotfiles repo: canonical skills under ai/skills + external-skills.txt."""
    root = tmp_path / "dotfiles"
    spec: dict[str, str | None] = {f"ai/skills/{name}/SKILL.md": "---\n" for name in canonical}
    spec["ai/agents/claude/external-skills.txt"] = external
    write_tree(root, spec)
    return root


def _home_with_skills(tmp_path: Path, layout: dict[str, list[str]]) -> Path:
    """Build $HOME with deployed skill dirs, e.g. {'.agents/skills': ['align', 'review']}."""
    home = tmp_path / "home"
    spec: dict[str, str | None] = {}
    for location, names in layout.items():
        for name in names:
            spec[f"{location}/{name}/SKILL.md"] = "x"
    write_tree(home, spec)
    return home


def test_external_skill_names_parses_owner_repo_at_skill(tmp_path: Path) -> None:
    root = _dotfiles(
        tmp_path,
        canonical=[],
        external=(
            "# comment line\n"
            "fastapi/fastapi@fastapi\n"
            "cloudflare/skills@building-mcp-server-on-cloudflare   # inline note\n"
            "\n"
            "hairyf/skills@tauri\n"
        ),
    )
    assert external_skill_names(root) == {"fastapi", "building-mcp-server-on-cloudflare", "tauri"}


def test_find_orphans_classifies_retired_vs_untracked(tmp_path: Path) -> None:
    # canonical now: form-align (renamed from align). external: tauri.
    dotfiles = _dotfiles(tmp_path, canonical=["form-align", "review"], external="x/y@tauri")
    home = _home_with_skills(
        tmp_path,
        {
            ".agents/skills": ["form-align", "review", "tauri", "align", "vitest"],
        },
    )
    # git history once had ai/skills/align (ours, since renamed); never had vitest.
    runner = _git_history(dotfiles, ".ai/skills/align/SKILL.md", "ai/skills/form-align/SKILL.md")

    orphans = find_orphans(runner, home, dotfiles)
    by_name = {o.name: o for o in orphans}

    # canonical + external are kept (not orphans)
    assert "form-align" not in by_name
    assert "review" not in by_name
    assert "tauri" not in by_name
    # align: was ours → retired; vitest: never ours → untracked
    assert by_name["align"].retired is True
    assert by_name["vitest"].retired is False


def test_prune_orphans_deletes_only_retired(tmp_path: Path) -> None:
    dotfiles = _dotfiles(tmp_path, canonical=["form-align"])
    home = _home_with_skills(tmp_path, {".agents/skills": ["align", "vitest"]})
    runner = _git_history(dotfiles, ".ai/skills/align/SKILL.md")

    orphans = find_orphans(runner, home, dotfiles)
    steps = prune_orphans(orphans, dry_run=False)

    assert not (home / ".agents" / "skills" / "align").exists()  # retired → deleted
    assert (home / ".agents" / "skills" / "vitest").exists()  # untracked → kept
    assert any("Removed" in s.message and "align" in s.message for s in steps)


def test_prune_orphans_dry_run_deletes_nothing(tmp_path: Path) -> None:
    dotfiles = _dotfiles(tmp_path, canonical=["form-align"])
    home = _home_with_skills(tmp_path, {".agents/skills": ["align"]})
    runner = _git_history(dotfiles, ".ai/skills/align/SKILL.md")

    orphans = find_orphans(runner, home, dotfiles)
    steps = prune_orphans(orphans, dry_run=True)

    assert (home / ".agents" / "skills" / "align").exists()
    assert all("DRY RUN" in s.message for s in steps)
