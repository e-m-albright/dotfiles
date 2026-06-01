"""Skill and agent file validation service.

Mirrors the behavior of agents/shared/validate-skills.sh:
- Iterates .ai/skills/*/ dirs → each must have SKILL.md; validates with kind="skill"
- Iterates .ai/agents/*.md → validates each with kind="agent"
- Reports FileValidation per file; summary available from the list.

Exit semantics: any status=="fail" → non-zero exit (caller's responsibility).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_cli.core.models import FileValidation, FileValidationStatus

if TYPE_CHECKING:
    from dotfiles_cli.core.ports import FileSystem

# Compiled once; matches standalone MUST/ALWAYS/NEVER (word-boundary, not
# adjacent to [A-Za-z0-9_]).
_CAPS_RE = re.compile(r"(?<![A-Za-z0-9_])(?:MUST|ALWAYS|NEVER)(?![A-Za-z0-9_])")

# Name must match this pattern.
_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

_TRIGGER_RE = re.compile(r"(?<!\w)(?:use when|trigger when)(?!\w)", re.IGNORECASE)

_BODY_LIMIT: dict[str, int] = {"skill": 500, "agent": 200}
_DESC_MAX = 1024
_DESC_MIN = 20
_CAPS_THRESHOLD = 15


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    """Return (frontmatter_fields, body_lines).

    Frontmatter is the YAML block delimited by the first two ``---`` lines.
    Only single-line ``key: value`` entries are extracted.
    Returns (fields_dict, body_lines) where body_lines excludes the frontmatter.
    """
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        return {}, lines  # no frontmatter — caller will detect missing FM

    fm_end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.rstrip() == "---":
            fm_end = i
            break

    if fm_end is None:
        return {}, []  # unclosed frontmatter -> body undefined (matches Bash awk = 0)

    fm_lines = lines[1:fm_end]
    body_lines = lines[fm_end + 1 :]

    fields: dict[str, str] = {}
    for line in fm_lines:
        if ": " in line:
            key, _, value = line.partition(": ")
            fields[key.strip()] = value.strip()
        elif line.endswith(":"):
            fields[line[:-1].strip()] = ""

    return fields, body_lines


def _count_caps(body_lines: list[str]) -> int:
    """Count standalone MUST/ALWAYS/NEVER occurrences in the body."""
    return sum(len(_CAPS_RE.findall(line)) for line in body_lines)


# ---------------------------------------------------------------------------
# Rule helpers (each adds to errors/warnings in-place; complexity ≤ 4 each)
# ---------------------------------------------------------------------------


def _check_name(name: str, expected_name: str, errors: list[str], warnings: list[str]) -> None:
    if name != expected_name:
        errors.append(f"name '{name}' != expected '{expected_name}'")
    if not _NAME_RE.match(name):
        errors.append(f"name '{name}' violates [a-z0-9-] (no consec/leading/trailing hyphens)")


def _check_description(desc: str, errors: list[str], warnings: list[str]) -> None:
    if not desc:
        errors.append("missing description")
        return
    if len(desc) > _DESC_MAX:
        errors.append(f"description {len(desc)} chars > {_DESC_MAX}")
    elif len(desc) < _DESC_MIN:
        warnings.append(f"description {len(desc)} chars < {_DESC_MIN} (EMPTY_DESCRIPTION)")
    if not _TRIGGER_RE.search(desc):
        warnings.append("description lacks 'Use when' trigger clause (MISSING_TRIGGER)")


def _check_body(body_lines: list[str], kind: str, errors: list[str], warnings: list[str]) -> None:
    limit = _BODY_LIMIT.get(kind, 500)
    n = len(body_lines)
    if n > limit:
        warnings.append(f"body {n} lines > {limit} ({kind} cap)")
    caps = _count_caps(body_lines)
    if caps > _CAPS_THRESHOLD:
        warnings.append(
            f"{caps} instances of MUST/ALWAYS/NEVER in caps"
            f" (OVER_CONSTRAINED, threshold {_CAPS_THRESHOLD})"
        )


def _derive_status(errors: list[str], warnings: list[str]) -> FileValidationStatus:
    if errors:
        return "fail"
    if warnings:
        return "warn"
    return "ok"


# ---------------------------------------------------------------------------
# Core validation logic
# ---------------------------------------------------------------------------


def validate_file(
    text: str,
    *,
    kind: str,
    expected_name: str,
    rel_path: str,
) -> FileValidation:
    """Validate one skill or agent file text; return a FileValidation."""
    lines = text.splitlines()
    errors: list[str] = []
    warnings: list[str] = []

    if not lines or lines[0].rstrip() != "---":
        return FileValidation(
            rel_path=rel_path,
            kind=kind,
            status="fail",
            errors=("missing frontmatter",),
        )

    fields, body_lines = _parse_frontmatter(text)
    _check_name(fields.get("name", ""), expected_name, errors, warnings)
    _check_description(fields.get("description", ""), errors, warnings)
    _check_body(body_lines, kind, errors, warnings)

    return FileValidation(
        rel_path=rel_path,
        kind=kind,
        status=_derive_status(errors, warnings),
        body_lines=len(body_lines),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SkillValidateService:
    """Validate all skills and agents in the dotfiles repo."""

    def __init__(self, *, fs: FileSystem, dotfiles_dir: Path) -> None:
        self._fs = fs
        self._dotfiles_dir = dotfiles_dir

    def validate(self) -> list[FileValidation]:
        results: list[FileValidation] = []
        results.extend(self._validate_skills())
        results.extend(self._validate_agents())
        return results

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _validate_skills(self) -> list[FileValidation]:
        skills_root = self._dotfiles_dir / ".ai" / "skills"
        if not self._fs.exists(skills_root) or not self._fs.is_dir(skills_root):
            return []

        results: list[FileValidation] = []
        for entry in sorted(self._fs.iterdir(skills_root), key=lambda p: p.name):
            if not self._fs.is_dir(entry):
                continue
            skill_md = entry / "SKILL.md"
            rel_dir = str(entry.relative_to(self._dotfiles_dir)) + "/"
            if not self._fs.exists(skill_md):
                results.append(
                    FileValidation(
                        rel_path=rel_dir,
                        kind="skill",
                        status="fail",
                        errors=("missing SKILL.md",),
                    )
                )
                continue
            text = self._fs.read_text(skill_md)
            rel = str(skill_md.relative_to(self._dotfiles_dir))
            results.append(
                validate_file(text, kind="skill", expected_name=entry.name, rel_path=rel)
            )
        return results

    def _validate_agents(self) -> list[FileValidation]:
        agents_root = self._dotfiles_dir / ".ai" / "agents"
        if not self._fs.exists(agents_root) or not self._fs.is_dir(agents_root):
            return []

        results: list[FileValidation] = []
        for entry in sorted(self._fs.iterdir(agents_root), key=lambda p: p.name):
            if self._fs.is_dir(entry) or entry.suffix != ".md":
                continue
            text = self._fs.read_text(entry)
            rel = str(entry.relative_to(self._dotfiles_dir))
            expected = entry.stem
            results.append(validate_file(text, kind="agent", expected_name=expected, rel_path=rel))
        return results
