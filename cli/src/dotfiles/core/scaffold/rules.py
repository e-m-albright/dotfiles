"""Copy .ai/rules/ files into a project directory with a manifest header.

Faithful port of copy_ai_rule() + add_manifest_header() from scaffold.sh.
"""

from __future__ import annotations

from pathlib import Path

from dotfiles.core.models import StepResult

_DEFAULT_TODAY = "2026-01-01"
_MANIFEST_PREFIX = "<!-- source: dotfiles/.ai/rules/"


def _manifest_header(rule_path: str, today: str) -> str:
    """Return the single-line manifest header for a copied rule file."""
    return f"{_MANIFEST_PREFIX}{rule_path} | {today} -->"


def add_manifest_header(dest: Path, rule_path: str, today: str) -> None:
    """Prepend (or replace) the manifest header on *dest*.

    If the file already begins with a ``<!-- source:`` header, replace that
    line.  Otherwise prepend a new header line.  Byte-exact for --force
    idempotency — mirrors the mktemp dance in scaffold.sh.
    """
    header = _manifest_header(rule_path, today)
    existing = dest.read_text()
    lines = existing.splitlines(keepends=True)

    if lines and lines[0].startswith("<!-- source:"):
        # Replace existing header
        new_content = header + "\n" + "".join(lines[1:])
    else:
        # Prepend header
        new_content = header + "\n" + existing

    dest.write_text(new_content)


def copy_ai_rule(
    dotfiles_dir: Path,
    project_dir: Path,
    rule_path: str,
    *,
    force: bool = False,
    today: str = _DEFAULT_TODAY,
) -> StepResult:
    """Copy *dotfiles_dir*/.ai/rules/<rule_path> into *project_dir*/.ai/rules/.

    - Skips if destination already exists and *force* is False.
    - On --force: overwrites and replaces the manifest header in-place.
    - Always adds/updates the manifest header after copying.

    Returns a StepResult describing the outcome.
    """
    rule_name = Path(rule_path).name
    source = dotfiles_dir / ".ai" / "rules" / rule_path
    dest_dir = project_dir / ".ai" / "rules"
    dest = dest_dir / rule_name

    if not source.is_file():
        return StepResult(
            level="warn",
            message=f"Rule not found in dotfiles: {rule_path}",
        )

    dest_dir.mkdir(parents=True, exist_ok=True)

    if dest.is_file() and not force:
        return StepResult(level="info", message=f"skip .ai/rules/{rule_name}")

    import shutil

    shutil.copy2(source, dest)
    add_manifest_header(dest, rule_path, today)

    if force:
        return StepResult(
            level="success",
            message=f".ai/rules/{rule_name} (force copied)",
        )
    return StepResult(level="success", message=f"Copied .ai/rules/{rule_name}")
