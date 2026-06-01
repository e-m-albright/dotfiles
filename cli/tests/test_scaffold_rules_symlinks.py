"""Tests for core/scaffold/rules.py, symlinks.py, and gitignore.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from dotfiles.core.scaffold.gitignore import update_gitignore
from dotfiles.core.scaffold.rules import _manifest_header, add_manifest_header, copy_ai_rule
from dotfiles.core.scaffold.symlinks import (
    generate_root_symlinks,
    setup_tool_symlinks,
)
from dotfiles.core.scaffold.tool_registry import ToolTarget

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dotfiles(tmp_path: Path) -> Path:
    """Create a fake dotfiles dir with a minimal .ai/rules/ tree."""
    d = tmp_path / "dotfiles"
    rules = d / ".ai" / "rules"
    (rules / "languages").mkdir(parents=True)
    (rules / "frameworks").mkdir(parents=True)
    (rules / "languages" / "python.mdc").write_text("# python rule\n")
    (rules / "frameworks" / "fastapi.mdc").write_text("# fastapi rule\n")
    return d


def _make_project(tmp_path: Path) -> Path:
    p = tmp_path / "myproject"
    p.mkdir()
    return p


# ---------------------------------------------------------------------------
# rules.py — _manifest_header
# ---------------------------------------------------------------------------


class TestManifestHeader:
    def test_exact_format(self) -> None:
        h = _manifest_header("languages/python.mdc", "2026-05-31")
        assert h == "<!-- source: dotfiles/.ai/rules/languages/python.mdc | 2026-05-31 -->"

    def test_different_rule_path(self) -> None:
        h = _manifest_header("frameworks/fastapi.mdc", "2024-01-15")
        assert h == "<!-- source: dotfiles/.ai/rules/frameworks/fastapi.mdc | 2024-01-15 -->"


# ---------------------------------------------------------------------------
# rules.py — add_manifest_header
# ---------------------------------------------------------------------------


class TestAddManifestHeader:
    def test_prepends_header_to_file_without_one(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.mdc"
        f.write_text("# body\n")
        add_manifest_header(f, "languages/python.mdc", "2026-05-31")
        lines = f.read_text().splitlines()
        assert lines[0] == "<!-- source: dotfiles/.ai/rules/languages/python.mdc | 2026-05-31 -->"
        assert lines[1] == "# body"

    def test_replaces_existing_header(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.mdc"
        f.write_text(
            "<!-- source: dotfiles/.ai/rules/languages/python.mdc | 2025-01-01 -->\n# body\n"
        )
        add_manifest_header(f, "languages/python.mdc", "2026-05-31")
        lines = f.read_text().splitlines()
        assert lines[0] == "<!-- source: dotfiles/.ai/rules/languages/python.mdc | 2026-05-31 -->"
        assert lines[1] == "# body"
        assert len(lines) == 2

    def test_idempotent_force_replace(self, tmp_path: Path) -> None:
        """Calling twice with same date yields identical content — byte-exact."""
        f = tmp_path / "rule.mdc"
        f.write_text("# body\n")
        add_manifest_header(f, "languages/python.mdc", "2026-05-31")
        first = f.read_text()
        add_manifest_header(f, "languages/python.mdc", "2026-05-31")
        second = f.read_text()
        assert first == second

    def test_header_does_not_duplicate_body(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.mdc"
        f.write_text("line1\nline2\n")
        add_manifest_header(f, "x.mdc", "2026-01-01")
        content = f.read_text()
        assert content.count("line1") == 1
        assert content.count("line2") == 1


# ---------------------------------------------------------------------------
# rules.py — copy_ai_rule
# ---------------------------------------------------------------------------


class TestCopyAiRule:
    def test_copies_rule_and_adds_header(self, tmp_path: Path) -> None:
        dotfiles_dir = _make_dotfiles(tmp_path)
        project_dir = _make_project(tmp_path)
        result = copy_ai_rule(dotfiles_dir, project_dir, "languages/python.mdc", today="2026-05-31")
        assert result.level == "success"
        dest = project_dir / ".ai" / "rules" / "python.mdc"
        assert dest.is_file()
        first_line = dest.read_text().splitlines()[0]
        assert first_line == (
            "<!-- source: dotfiles/.ai/rules/languages/python.mdc | 2026-05-31 -->"
        )

    def test_skips_existing_without_force(self, tmp_path: Path) -> None:
        dotfiles_dir = _make_dotfiles(tmp_path)
        project_dir = _make_project(tmp_path)
        dest = project_dir / ".ai" / "rules"
        dest.mkdir(parents=True)
        (dest / "python.mdc").write_text("# custom\n")
        result = copy_ai_rule(dotfiles_dir, project_dir, "languages/python.mdc")
        assert result.level == "info"
        assert (dest / "python.mdc").read_text() == "# custom\n"

    def test_force_overwrites_existing(self, tmp_path: Path) -> None:
        dotfiles_dir = _make_dotfiles(tmp_path)
        project_dir = _make_project(tmp_path)
        dest_dir = project_dir / ".ai" / "rules"
        dest_dir.mkdir(parents=True)
        (dest_dir / "python.mdc").write_text("# old\n")
        result = copy_ai_rule(
            dotfiles_dir, project_dir, "languages/python.mdc", force=True, today="2026-05-31"
        )
        assert result.level == "success"
        content = (dest_dir / "python.mdc").read_text()
        assert "# python rule" in content
        assert "<!-- source:" in content

    def test_warns_on_missing_source(self, tmp_path: Path) -> None:
        dotfiles_dir = _make_dotfiles(tmp_path)
        project_dir = _make_project(tmp_path)
        result = copy_ai_rule(dotfiles_dir, project_dir, "nonexistent/rule.mdc")
        assert result.level == "warn"

    def test_creates_dest_dir_if_absent(self, tmp_path: Path) -> None:
        dotfiles_dir = _make_dotfiles(tmp_path)
        project_dir = _make_project(tmp_path)
        copy_ai_rule(dotfiles_dir, project_dir, "languages/python.mdc", today="2026-05-31")
        assert (project_dir / ".ai" / "rules" / "python.mdc").is_file()

    def test_force_result_message_says_force(self, tmp_path: Path) -> None:
        dotfiles_dir = _make_dotfiles(tmp_path)
        project_dir = _make_project(tmp_path)
        result = copy_ai_rule(
            dotfiles_dir, project_dir, "languages/python.mdc", force=True, today="2026-05-31"
        )
        assert "force" in result.message.lower()


# ---------------------------------------------------------------------------
# symlinks.py — setup_tool_symlinks
# ---------------------------------------------------------------------------


def _cursor_tool() -> ToolTarget:
    return ToolTarget.model_validate(
        {
            "rulesDir": ".cursor/rules",
            "suffix": ".mdc",
            "strategy": "symlink",
            "symlinkPrefix": "../../",
            "rootFile": None,
        }
    )


def _copilot_tool() -> ToolTarget:
    return ToolTarget.model_validate(
        {
            "rulesDir": ".github/instructions",
            "suffix": ".instructions.md",
            "strategy": "symlink",
            "symlinkPrefix": "../../",
            "rootFile": None,
        }
    )


class TestSetupToolSymlinks:
    def _seed_rules(self, project_dir: Path, names: list[str]) -> None:
        rules_dir = project_dir / ".ai" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        for name in names:
            (rules_dir / name).write_text(f"# {name}\n")

    def test_creates_cursor_symlinks_with_correct_target(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        self._seed_rules(project_dir, ["python.mdc", "fastapi.mdc"])

        tools = {"cursor": _cursor_tool()}
        setup_tool_symlinks(project_dir, tools)

        link = project_dir / ".cursor" / "rules" / "python.mdc"
        assert link.is_symlink()
        # Target is string-concatenated prefix + path, NOT relpath
        assert str(link.readlink()) == "../../.ai/rules/python.mdc"

    def test_symlink_target_uses_prefix_string_concat_not_relpath(self, tmp_path: Path) -> None:
        """The prefix from the registry must be concatenated verbatim."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        self._seed_rules(project_dir, ["python.mdc"])

        tools = {"cursor": _cursor_tool()}
        setup_tool_symlinks(project_dir, tools)

        link = project_dir / ".cursor" / "rules" / "python.mdc"
        target = str(link.readlink())
        # Must start with the registry prefix "../../"
        assert target.startswith("../../")
        # NOT the os.path.relpath equivalent
        assert target == "../../.ai/rules/python.mdc"

    def test_copilot_uses_instructions_suffix(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        self._seed_rules(project_dir, ["python.mdc"])

        tools = {"copilot": _copilot_tool()}
        setup_tool_symlinks(project_dir, tools)

        link = project_dir / ".github" / "instructions" / "python.instructions.md"
        assert link.is_symlink()
        assert str(link.readlink()) == "../../.ai/rules/python.mdc"

    def test_idempotent_correct_symlink_not_touched(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        self._seed_rules(project_dir, ["python.mdc"])

        tools = {"cursor": _cursor_tool()}
        setup_tool_symlinks(project_dir, tools)
        link = project_dir / ".cursor" / "rules" / "python.mdc"
        mtime1 = link.lstat().st_mtime

        setup_tool_symlinks(project_dir, tools)
        mtime2 = link.lstat().st_mtime
        assert mtime1 == mtime2  # not recreated

    def test_stale_symlink_replaced(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        self._seed_rules(project_dir, ["python.mdc"])

        rules_link_dir = project_dir / ".cursor" / "rules"
        rules_link_dir.mkdir(parents=True)
        stale_link = rules_link_dir / "python.mdc"
        stale_link.symlink_to("old-target")

        tools = {"cursor": _cursor_tool()}
        setup_tool_symlinks(project_dir, tools)

        assert str(stale_link.readlink()) == "../../.ai/rules/python.mdc"

    def test_plain_file_preserved_without_force(self, tmp_path: Path) -> None:
        """A real file at the tool-link path is left untouched without --force."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        self._seed_rules(project_dir, ["python.mdc"])

        rules_link_dir = project_dir / ".cursor" / "rules"
        rules_link_dir.mkdir(parents=True)
        real_file = rules_link_dir / "python.mdc"
        real_file.write_text("# hand-placed real file\n")

        tools = {"cursor": _cursor_tool()}
        setup_tool_symlinks(project_dir, tools)

        assert not real_file.is_symlink()
        assert real_file.read_text() == "# hand-placed real file\n"

    def test_plain_file_replaced_with_force(self, tmp_path: Path) -> None:
        """--force removes the real file and relinks it to .ai/rules/."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        self._seed_rules(project_dir, ["python.mdc"])

        rules_link_dir = project_dir / ".cursor" / "rules"
        rules_link_dir.mkdir(parents=True)
        real_file = rules_link_dir / "python.mdc"
        real_file.write_text("# hand-placed real file\n")

        tools = {"cursor": _cursor_tool()}
        setup_tool_symlinks(project_dir, tools, force=True)

        assert real_file.is_symlink()
        assert str(real_file.readlink()) == "../../.ai/rules/python.mdc"

    def test_no_rules_dir_no_crash(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        # No .ai/rules/ dir at all
        tools = {"cursor": _cursor_tool()}
        setup_tool_symlinks(project_dir, tools)  # must not raise

    def test_tool_with_null_rules_dir_skipped(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        self._seed_rules(project_dir, ["python.mdc"])

        codex = ToolTarget.model_validate(
            {
                "rulesDir": None,
                "suffix": None,
                "strategy": "symlink",
                "symlinkPrefix": None,
                "rootFile": "CODEX.md",
            }
        )
        setup_tool_symlinks(project_dir, {"codex": codex})
        # No .cursor/rules created
        assert not (project_dir / ".cursor").exists()


# ---------------------------------------------------------------------------
# symlinks.py — generate_root_symlinks
# ---------------------------------------------------------------------------


class TestGenerateRootSymlinks:
    def _codex_tool(self) -> ToolTarget:
        return ToolTarget.model_validate(
            {
                "rulesDir": None,
                "suffix": None,
                "strategy": "symlink",
                "symlinkPrefix": None,
                "rootFile": "CODEX.md",
            }
        )

    def test_creates_root_symlink(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        (project_dir / "AGENTS.md").write_text("# agents\n")

        created = generate_root_symlinks(project_dir, {"codex": self._codex_tool()})
        link = project_dir / "CODEX.md"
        assert link.is_symlink()
        assert str(link.readlink()) == "AGENTS.md"
        assert "CODEX.md" in created

    def test_idempotent_correct_symlink_skipped(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        (project_dir / "AGENTS.md").write_text("# agents\n")

        generate_root_symlinks(project_dir, {"codex": self._codex_tool()})
        created = generate_root_symlinks(project_dir, {"codex": self._codex_tool()})
        assert created == []

    def test_existing_file_skipped_without_force(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        (project_dir / "CODEX.md").write_text("# owned\n")

        created = generate_root_symlinks(project_dir, {"codex": self._codex_tool()}, force=False)
        assert created == []
        assert not (project_dir / "CODEX.md").is_symlink()

    def test_existing_file_replaced_with_force(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        (project_dir / "CODEX.md").write_text("# owned\n")

        created = generate_root_symlinks(project_dir, {"codex": self._codex_tool()}, force=True)
        assert "CODEX.md" in created
        assert (project_dir / "CODEX.md").is_symlink()

    def test_tool_with_no_root_file_skipped(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        cursor = _cursor_tool()
        created = generate_root_symlinks(project_dir, {"cursor": cursor})
        assert created == []


# ---------------------------------------------------------------------------
# gitignore.py
# ---------------------------------------------------------------------------


class TestUpdateGitignore:
    def test_creates_gitignore_with_artifacts_and_tool_rules(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        appended = update_gitignore(project_dir, [".cursor/rules/"])
        assert "artifacts" in appended
        assert "tool-rules" in appended
        content = (project_dir / ".gitignore").read_text()
        assert ".ai/artifacts/" in content
        assert ".cursor/rules/" in content

    def test_idempotent_second_call_no_change(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        update_gitignore(project_dir, [".cursor/rules/"])
        content1 = (project_dir / ".gitignore").read_text()

        appended2 = update_gitignore(project_dir, [".cursor/rules/"])
        content2 = (project_dir / ".gitignore").read_text()
        assert appended2 == []
        assert content1 == content2

    def test_appends_to_existing_gitignore(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        (project_dir / ".gitignore").write_text("node_modules/\n")
        update_gitignore(project_dir, [".cursor/rules/"])
        content = (project_dir / ".gitignore").read_text()
        assert "node_modules/" in content
        assert ".ai/artifacts/" in content

    def test_artifacts_block_not_doubled(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        # Pre-seed with the artifacts marker already present
        (project_dir / ".gitignore").write_text(".ai/artifacts/\n")
        update_gitignore(project_dir, [".cursor/rules/"])
        content = (project_dir / ".gitignore").read_text()
        assert content.count(".ai/artifacts/") == 1

    def test_no_entries_skips_tool_rules_section(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        appended = update_gitignore(project_dir, [])
        assert "tool-rules" not in appended

    def test_decisions_dir_not_gitignored(self, tmp_path: Path) -> None:
        """decisions/ must be exempted — it's versioned."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        update_gitignore(project_dir, [])
        content = (project_dir / ".gitignore").read_text()
        assert "!.ai/artifacts/decisions/" in content

    @pytest.mark.parametrize("entry", [".cursor/rules/", ".github/instructions/", "CODEX.md"])
    def test_various_tool_entries(self, tmp_path: Path, entry: str) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        update_gitignore(project_dir, [entry])
        content = (project_dir / ".gitignore").read_text()
        assert entry in content
