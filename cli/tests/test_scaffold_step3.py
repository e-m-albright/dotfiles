"""Tests for scaffold step 3 modules:
agents_md, artifacts, optional_scaffolds, preflight, project_rename, templates.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from dotfiles.core.scaffold.agents_md import generate_agents_md, write_agents_md
from dotfiles.core.scaffold.artifacts import create_artifacts_dir
from dotfiles.core.scaffold.optional_scaffolds import (
    deploy_agent_rules_sync,
    deploy_audit_pipeline,
    deploy_baselines,
)
from dotfiles.core.scaffold.preflight import check_command, preflight
from dotfiles.core.scaffold.project_rename import update_project_name
from dotfiles.core.scaffold.templates import copy_template_files

# ---------------------------------------------------------------------------
# agents_md.py
# ---------------------------------------------------------------------------


class TestGenerateAgentsMd:
    def test_returns_string(self) -> None:
        content = generate_agents_md("myproject")
        assert isinstance(content, str)
        assert len(content) > 100

    def test_contains_key_sections(self) -> None:
        content = generate_agents_md("myproject")
        assert "## Critical Rules" in content
        assert "## Project Context" in content
        assert "## Proof of Life" in content
        assert "orangutan" in content

    def test_contains_agents_md_header(self) -> None:
        content = generate_agents_md("myproject")
        assert content.startswith("# AGENTS.md")

    def test_never_has_empty_output(self) -> None:
        assert generate_agents_md("") != ""
        assert generate_agents_md("anything") != ""


class TestWriteAgentsMd:
    def test_writes_file(self, tmp_path: Path) -> None:
        result = write_agents_md(tmp_path, "myproject")
        assert result.level == "success"
        assert (tmp_path / "AGENTS.md").is_file()

    def test_skips_existing_without_force(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# custom\n")
        result = write_agents_md(tmp_path, "myproject", force=False)
        assert result.level == "info"
        assert (tmp_path / "AGENTS.md").read_text() == "# custom\n"

    def test_force_overwrites(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# old\n")
        result = write_agents_md(tmp_path, "myproject", force=True)
        assert result.level == "success"
        assert "# AGENTS.md" in (tmp_path / "AGENTS.md").read_text()

    def test_force_message_says_regenerated(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# old\n")
        result = write_agents_md(tmp_path, "myproject", force=True)
        assert "regenerated" in result.message.lower()

    def test_written_content_passes_key_section_check(self, tmp_path: Path) -> None:
        write_agents_md(tmp_path, "myproject")
        content = (tmp_path / "AGENTS.md").read_text()
        assert "## Critical Rules" in content


# ---------------------------------------------------------------------------
# artifacts.py
# ---------------------------------------------------------------------------


class TestCreateArtifactsDir:
    def test_creates_all_subdirs(self, tmp_path: Path) -> None:
        create_artifacts_dir(tmp_path)
        for sub in ("plans", "research", "decisions", "sessions"):
            assert (tmp_path / ".ai" / "artifacts" / sub).is_dir()

    def test_seeds_readme(self, tmp_path: Path) -> None:
        create_artifacts_dir(tmp_path)
        readme = tmp_path / ".ai" / "artifacts" / "README.md"
        assert readme.is_file()
        assert "Working Files" in readme.read_text()

    def test_seeds_decisions_index(self, tmp_path: Path) -> None:
        create_artifacts_dir(tmp_path)
        idx = tmp_path / ".ai" / "artifacts" / "decisions" / "_index.md"
        assert idx.is_file()
        assert "Architecture Decision Records" in idx.read_text()

    def test_idempotent_no_overwrite_readme(self, tmp_path: Path) -> None:
        create_artifacts_dir(tmp_path)
        readme = tmp_path / ".ai" / "artifacts" / "README.md"
        readme.write_text("# custom\n")
        create_artifacts_dir(tmp_path)
        assert readme.read_text() == "# custom\n"

    def test_idempotent_no_overwrite_decisions_index(self, tmp_path: Path) -> None:
        create_artifacts_dir(tmp_path)
        idx = tmp_path / ".ai" / "artifacts" / "decisions" / "_index.md"
        idx.write_text("# mine\n")
        create_artifacts_dir(tmp_path)
        assert idx.read_text() == "# mine\n"

    def test_decisions_subdir_committed_not_ephemeral(self, tmp_path: Path) -> None:
        """The decisions/ dir must exist (it's versioned, unlike the rest)."""
        create_artifacts_dir(tmp_path)
        assert (tmp_path / ".ai" / "artifacts" / "decisions").is_dir()


# ---------------------------------------------------------------------------
# optional_scaffolds.py — helpers
# ---------------------------------------------------------------------------


def _make_dotfiles_with_scaffold(tmp_path: Path, scaffold_name: str, files: list[str]) -> Path:
    """Create a fake dotfiles dir with scaffold source files."""
    d = tmp_path / "dotfiles"
    base = d / "prompts" / "scaffolds" / scaffold_name
    for rel in files:
        f = base / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"# {rel}\n")
    return d


class TestDeployAuditPipeline:
    _FILES: ClassVar[list[str]] = [
        "scripts/audit/security.sh",
        "scripts/audit/ai_usage.py",
        "just/audit/mod.just",
        ".ai/prompts/audits/security.md",
        ".ai/prompts/audits/ai-usage.md",
    ]

    def test_deploys_all_files(self, tmp_path: Path) -> None:
        dotfiles_dir = _make_dotfiles_with_scaffold(tmp_path, "audit-pipeline", self._FILES)
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        results = deploy_audit_pipeline(dotfiles_dir, project_dir)
        successes = [r for r in results if r.level == "success"]
        assert len(successes) == len(self._FILES)
        for rel in self._FILES:
            assert (project_dir / rel).is_file()

    def test_skips_existing_without_force(self, tmp_path: Path) -> None:
        dotfiles_dir = _make_dotfiles_with_scaffold(tmp_path, "audit-pipeline", self._FILES)
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        # Pre-create one file
        existing = project_dir / "scripts" / "audit" / "security.sh"
        existing.parent.mkdir(parents=True)
        existing.write_text("# mine\n")

        results = deploy_audit_pipeline(dotfiles_dir, project_dir)
        skips = [r for r in results if r.level == "info"]
        assert len(skips) == 1
        assert existing.read_text() == "# mine\n"

    def test_force_overwrites(self, tmp_path: Path) -> None:
        dotfiles_dir = _make_dotfiles_with_scaffold(tmp_path, "audit-pipeline", self._FILES)
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        existing = project_dir / "scripts" / "audit" / "security.sh"
        existing.parent.mkdir(parents=True)
        existing.write_text("# old\n")

        results = deploy_audit_pipeline(dotfiles_dir, project_dir, force=True)
        successes = [r for r in results if r.level == "success"]
        assert any("security.sh" in r.message for r in successes)


class TestDeployBaselines:
    _FILES: ClassVar[list[str]] = ["baselines.json", "scripts/check_baselines.py"]
    _LH = "lefthook.baselines.yml"

    def _seed(self, tmp_path: Path) -> Path:
        d = _make_dotfiles_with_scaffold(tmp_path, "baselines", self._FILES)
        # Also seed the lefthook fragment
        lh = d / "prompts" / "scaffolds" / "baselines" / self._LH
        lh.write_text("# lefthook\n")
        return d

    def test_deploys_files_and_lefthook(self, tmp_path: Path) -> None:
        dotfiles_dir = self._seed(tmp_path)
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        results = deploy_baselines(dotfiles_dir, project_dir)
        assert (project_dir / "baselines.json").is_file()
        assert (project_dir / "scripts" / "check_baselines.py").is_file()
        assert (project_dir / self._LH).is_file()
        assert any("lefthook" in r.message for r in results)

    def test_lefthook_not_forced(self, tmp_path: Path) -> None:
        dotfiles_dir = self._seed(tmp_path)
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        # Pre-create lefthook file
        (project_dir / self._LH).write_text("# mine\n")

        deploy_baselines(dotfiles_dir, project_dir, force=True)
        # lefthook should NOT be overwritten even with force
        assert (project_dir / self._LH).read_text() == "# mine\n"


class TestDeployAgentRulesSync:
    _FILES: ClassVar[list[str]] = ["scripts/sync-agent-rules.sh"]
    _LH = "lefthook.agent-rules.yml"

    def _seed(self, tmp_path: Path) -> Path:
        d = _make_dotfiles_with_scaffold(tmp_path, "agent-rules-sync", self._FILES)
        lh = d / "prompts" / "scaffolds" / "agent-rules-sync" / self._LH
        lh.write_text("# lefthook\n")
        return d

    def test_deploys_script_and_lefthook(self, tmp_path: Path) -> None:
        dotfiles_dir = self._seed(tmp_path)
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        results = deploy_agent_rules_sync(dotfiles_dir, project_dir)
        assert (project_dir / "scripts" / "sync-agent-rules.sh").is_file()
        assert (project_dir / self._LH).is_file()
        assert any("lefthook" in r.message for r in results)

    def test_missing_source_returns_warn(self, tmp_path: Path) -> None:
        dotfiles_dir = tmp_path / "dotfiles"
        dotfiles_dir.mkdir()
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        results = deploy_agent_rules_sync(dotfiles_dir, project_dir)
        assert any(r.level == "warn" for r in results)


# ---------------------------------------------------------------------------
# preflight.py
# ---------------------------------------------------------------------------


class TestCheckCommand:
    def test_found_returns_success(self) -> None:
        result = check_command(lambda _cmd: True, "git")
        assert result.level == "success"

    def test_missing_returns_warn(self) -> None:
        result = check_command(lambda _cmd: False, "bun")
        assert result.level == "warn"
        assert "bun" in result.message


class TestPreflight:
    def _all_present(self, _cmd: str) -> bool:
        return True

    def _all_missing(self, _cmd: str) -> bool:
        return False

    @pytest.mark.parametrize(
        ("recipe", "expected_cmd"),
        [
            ("typescript", "bun"),
            ("python", "uv"),
            ("golang", "go"),
            ("rust", "cargo"),
        ],
    )
    def test_recipe_tool_included(self, recipe: str, expected_cmd: str) -> None:
        results = preflight(recipe, self._all_present)
        cmds = [r.message for r in results]
        assert any(expected_cmd in m for m in cmds)

    def test_git_and_curl_always_checked(self) -> None:
        for recipe in ("typescript", "python", "golang", "rust"):
            results = preflight(recipe, self._all_present)
            msgs = " ".join(r.message for r in results)
            assert "git" in msgs
            assert "curl" in msgs

    def test_lefthook_optional_included(self) -> None:
        results = preflight("python", self._all_missing)
        msgs = " ".join(r.message for r in results)
        assert "lefthook" in msgs

    def test_all_missing_returns_warns(self) -> None:
        results = preflight("typescript", self._all_missing)
        assert all(r.level == "warn" for r in results)

    def test_all_present_returns_successes(self) -> None:
        results = preflight("python", self._all_present)
        assert all(r.level == "success" for r in results)

    def test_unknown_recipe_only_common_and_optional(self) -> None:
        results = preflight("elixir", self._all_present)
        # git + curl + lefthook = 3
        assert len(results) == 3


# ---------------------------------------------------------------------------
# project_rename.py
# ---------------------------------------------------------------------------


class TestUpdateProjectName:
    def test_renames_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "my-sveltekit-app"}\n')
        results = update_project_name(tmp_path, "my-app")
        assert any(r.level == "success" for r in results)
        content = (tmp_path / "package.json").read_text()
        assert '"my-app"' in content
        assert '"my-sveltekit-app"' not in content

    def test_renames_pyproject_toml(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "my-python-app"\n')
        results = update_project_name(tmp_path, "my-service")
        assert any(r.level == "success" for r in results)
        content = (tmp_path / "pyproject.toml").read_text()
        assert 'name = "my-service"' in content

    def test_renames_cargo_toml(self, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "my-rust-app"\n')
        results = update_project_name(tmp_path, "my-crate")
        assert any(r.level == "success" for r in results)
        assert 'name = "my-crate"' in (tmp_path / "Cargo.toml").read_text()

    def test_skips_missing_files(self, tmp_path: Path) -> None:
        results = update_project_name(tmp_path, "whatever")
        assert results == []

    def test_skips_file_without_placeholder(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "already-custom"}\n')
        results = update_project_name(tmp_path, "my-app")
        assert any(r.level == "info" for r in results)
        assert (tmp_path / "package.json").read_text() == '{"name": "already-custom"}\n'

    def test_only_first_occurrence_replaced(self, tmp_path: Path) -> None:
        """Matches sed -i 's/.../1' — replaces first occurrence only."""
        (tmp_path / "package.json").write_text(
            '{"name": "my-sveltekit-app", "other": "my-sveltekit-app"}\n'
        )
        update_project_name(tmp_path, "new-name")
        content = (tmp_path / "package.json").read_text()
        # First replaced, second untouched
        assert '"new-name"' in content
        assert content.count("my-sveltekit-app") == 1


# ---------------------------------------------------------------------------
# templates.py
# ---------------------------------------------------------------------------


class TestCopyTemplateFiles:
    def _make_dotfiles(self, tmp_path: Path, recipe: str, app_type: str) -> Path:
        d = tmp_path / "dotfiles"
        tdir = d / "prompts" / recipe / app_type / "templates"
        tdir.mkdir(parents=True)
        (tdir / "justfile").write_text("default:\n  echo hi\n")
        (tdir / ".env.example").write_text("PORT=3000\n")
        return d

    def _make_recipe_dotfiles(self, tmp_path: Path, recipe: str) -> Path:
        d = tmp_path / "dotfiles"
        tdir = d / "prompts" / recipe / "templates"
        tdir.mkdir(parents=True)
        (tdir / "README.md").write_text("# template\n")
        return d

    def test_copies_app_type_templates(self, tmp_path: Path) -> None:
        dotfiles_dir = self._make_dotfiles(tmp_path, "python", "fastapi")
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        result = copy_template_files(dotfiles_dir, project_dir, "python", "fastapi")
        assert result.level == "success"
        assert (project_dir / "justfile").is_file()
        assert (project_dir / ".env.example").is_file()

    def test_falls_back_to_recipe_templates(self, tmp_path: Path) -> None:
        dotfiles_dir = self._make_recipe_dotfiles(tmp_path, "golang")
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        result = copy_template_files(dotfiles_dir, project_dir, "golang", "chi")
        assert result.level == "success"
        assert (project_dir / "README.md").is_file()

    def test_app_type_preferred_over_recipe(self, tmp_path: Path) -> None:
        dotfiles_dir = tmp_path / "dotfiles"
        # Create both app-type and recipe templates
        (dotfiles_dir / "prompts" / "typescript" / "svelte" / "templates").mkdir(parents=True)
        (dotfiles_dir / "prompts" / "typescript" / "svelte" / "templates" / "app.ts").write_text(
            "// svelte\n"
        )
        (dotfiles_dir / "prompts" / "typescript" / "templates").mkdir(parents=True)
        (dotfiles_dir / "prompts" / "typescript" / "templates" / "generic.ts").write_text(
            "// generic\n"
        )
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        result = copy_template_files(dotfiles_dir, project_dir, "typescript", "svelte")
        assert result.level == "success"
        assert (project_dir / "app.ts").is_file()
        assert not (project_dir / "generic.ts").is_file()

    def test_no_template_dir_returns_info(self, tmp_path: Path) -> None:
        dotfiles_dir = tmp_path / "dotfiles"
        dotfiles_dir.mkdir()
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        result = copy_template_files(dotfiles_dir, project_dir, "rust", "axum")
        assert result.level == "info"

    def test_result_label_says_from_app_type(self, tmp_path: Path) -> None:
        dotfiles_dir = self._make_dotfiles(tmp_path, "python", "fastapi")
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        result = copy_template_files(dotfiles_dir, project_dir, "python", "fastapi")
        assert "fastapi" in result.message
