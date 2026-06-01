"""Tests for core/agent_setup/bake_rules.py.

All tests use tmp_path for dotfiles_dir — no real filesystem touched.
"""

from __future__ import annotations

from pathlib import Path

from dotfiles.core.agent_setup.bake_rules import _strip_frontmatter, bake_rules
from tests.fakes import write_tree

# ---------------------------------------------------------------------------
# _strip_frontmatter
# ---------------------------------------------------------------------------


class TestStripFrontmatter:
    def test_strips_yaml_block(self) -> None:
        """Faithful to awk: everything after the second --- is returned verbatim."""
        text = "---\ndescription: A rule\nalwaysApply: true\n---\n\n# Body\n\nContent here.\n"
        result = _strip_frontmatter(text)
        assert result == "\n# Body\n\nContent here.\n"

    def test_no_frontmatter_returns_as_is(self) -> None:
        text = "# Body\n\nNo frontmatter.\n"
        result = _strip_frontmatter(text)
        assert result == text

    def test_preserves_leading_blank_after_second_dashes(self) -> None:
        """awk prints whatever follows the second ---, including leading newlines."""
        text = "---\nkey: val\n---\n\n\nContent\n"
        result = _strip_frontmatter(text)
        assert result == "\n\nContent\n"

    def test_single_dashes_block_not_stripped(self) -> None:
        """Only one --- means no closed frontmatter; return as-is."""
        text = "---\nkey: val\n# Body\n"
        result = _strip_frontmatter(text)
        assert result == text

    def test_empty_string(self) -> None:
        assert _strip_frontmatter("") == ""

    def test_only_frontmatter_returns_empty(self) -> None:
        text = "---\nkey: val\n---\n"
        result = _strip_frontmatter(text)
        assert result == ""


# ---------------------------------------------------------------------------
# bake_rules
# ---------------------------------------------------------------------------

RULE_A = """\
---
description: Rule A
alwaysApply: true
---

# Alpha

Alpha content.
"""

RULE_B = """\
---
description: Rule B
---

# Beta

Beta content.
"""

RULE_NO_FM = "# Gamma\n\nGamma content.\n"


class TestBakeRules:
    def _make_dotfiles(self, tmp_path: Path, rules: dict[str, str]) -> Path:
        dotfiles = tmp_path / "dotfiles"
        tree: dict[str, str | None] = {
            f".ai/rules/process/{name}": content for name, content in rules.items()
        }
        write_tree(dotfiles, tree)
        return dotfiles

    def test_empty_when_no_rules_dir(self, tmp_path: Path) -> None:
        dotfiles = tmp_path / "dotfiles"
        dotfiles.mkdir()
        assert bake_rules(dotfiles) == ""

    def test_empty_when_no_mdc_files(self, tmp_path: Path) -> None:
        dotfiles = self._make_dotfiles(tmp_path, {})
        # Manually create the dir with no .mdc files
        (dotfiles / ".ai" / "rules" / "process").mkdir(parents=True, exist_ok=True)
        assert bake_rules(dotfiles) == ""

    def test_single_rule_stripped_and_wrapped(self, tmp_path: Path) -> None:
        dotfiles = self._make_dotfiles(tmp_path, {"alpha.mdc": RULE_A})
        result = bake_rules(dotfiles)
        # Preamble comes first, then separator, then rule section
        assert result.startswith("\n# Universal rules (baked from .ai/rules/process/)\n")
        assert "## alpha" in result
        assert "# Alpha" in result
        assert "Alpha content." in result
        # Frontmatter must not appear
        assert "description: Rule A" not in result
        assert "alwaysApply" not in result

    def test_multiple_rules_joined_by_separator(self, tmp_path: Path) -> None:
        dotfiles = self._make_dotfiles(tmp_path, {"alpha.mdc": RULE_A, "beta.mdc": RULE_B})
        result = bake_rules(dotfiles)
        assert "## alpha" in result
        assert "## beta" in result
        assert "\n---\n\n" in result

    def test_alphabetical_order(self, tmp_path: Path) -> None:
        dotfiles = self._make_dotfiles(
            tmp_path, {"zebra.mdc": RULE_A, "alpha.mdc": RULE_B, "middle.mdc": RULE_NO_FM}
        )
        result = bake_rules(dotfiles)
        alpha_pos = result.index("## alpha")
        middle_pos = result.index("## middle")
        zebra_pos = result.index("## zebra")
        assert alpha_pos < middle_pos < zebra_pos

    def test_rule_without_frontmatter(self, tmp_path: Path) -> None:
        dotfiles = self._make_dotfiles(tmp_path, {"gamma.mdc": RULE_NO_FM})
        result = bake_rules(dotfiles)
        assert "## gamma" in result
        assert "# Gamma" in result
        assert "Gamma content." in result

    def test_section_separator_count(self, tmp_path: Path) -> None:
        """N rules → N separators (preamble + N rule sections joined by \\n---\\n\\n)."""
        rules = {f"rule-{i:02d}.mdc": f"# Rule {i}\n\nContent.\n" for i in range(4)}
        dotfiles = self._make_dotfiles(tmp_path, rules)
        result = bake_rules(dotfiles)
        # preamble + 4 rules = 5 parts → 4 separators
        assert result.count("\n---\n\n") == 4

    def test_preamble_header_present(self, tmp_path: Path) -> None:
        """Output starts with the preamble header matching the old bash printf."""
        dotfiles = self._make_dotfiles(tmp_path, {"alpha.mdc": RULE_A})
        result = bake_rules(dotfiles)
        assert "\n# Universal rules (baked from .ai/rules/process/)\n" in result

    def test_preamble_italics_source_note(self, tmp_path: Path) -> None:
        """Output contains the italicised source note line."""
        dotfiles = self._make_dotfiles(tmp_path, {"alpha.mdc": RULE_A})
        result = bake_rules(dotfiles)
        assert "_These rules govern process, safety, and coding conventions" in result
        assert "*.mdc`._" in result

    def test_leading_separator_before_first_rule(self, tmp_path: Path) -> None:
        """First rule is preceded by \\n---\\n\\n (not directly after preamble)."""
        dotfiles = self._make_dotfiles(tmp_path, {"alpha.mdc": RULE_A})
        result = bake_rules(dotfiles)
        # preamble block ends, then separator, then rule
        preamble_end = result.index("*.mdc`._") + len("*.mdc`._")
        assert result[preamble_end : preamble_end + 8] == "\n---\n\n##"

    def test_name_is_stem_not_filename(self, tmp_path: Path) -> None:
        dotfiles = self._make_dotfiles(tmp_path, {"my-rule.mdc": RULE_A})
        result = bake_rules(dotfiles)
        assert "## my-rule\n" in result
        # .mdc appears only in preamble source path glob, not in rule headings
        assert "## my-rule.mdc" not in result

    def test_real_rule_format(self, tmp_path: Path) -> None:
        """Integration: verify the actual dotfiles process rules can be baked."""
        real_dotfiles = Path("/Users/evan/dotfiles")
        result = bake_rules(real_dotfiles)
        # Should produce non-empty output with preamble + section headers
        assert "# Universal rules (baked from .ai/rules/process/)" in result
        assert "_These rules govern process" in result
        assert "## " in result
        assert "\n---\n\n" in result
        # Must not contain raw frontmatter delimiters at the start of sections
        for section in result.split("\n---\n\n"):
            assert not section.lstrip().startswith("description:"), (
                f"Frontmatter leaked into section: {section[:80]}"
            )
