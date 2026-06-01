"""Substitute the project name into package manifest files.

Faithful port of the package.json / pyproject.toml / Cargo.toml sed blocks
in scaffold.sh.  Uses pathlib read/replace/write — no subprocess sed.
"""

from __future__ import annotations

from pathlib import Path

from dotfiles.core.models import StepResult

# Placeholder strings that appear in the recipe templates.
_PLACEHOLDERS: dict[str, str] = {
    "package.json": '"my-sveltekit-app"',
    "pyproject.toml": 'name = "my-python-app"',
    "Cargo.toml": 'name = "my-rust-app"',
}


def _replace_in_file(path: Path, old: str, new: str) -> bool:
    """Replace *old* with *new* in *path*.  Returns True if a change was made."""
    content = path.read_text()
    if old not in content:
        return False
    path.write_text(content.replace(old, new, 1))
    return True


def update_project_name(project_dir: Path, name: str) -> list[StepResult]:
    """Substitute the project name into manifest files in *project_dir*.

    Only touches files that exist and contain the expected placeholder.
    Returns a StepResult for each file attempted.
    """
    results: list[StepResult] = []

    replacements = {
        "package.json": ('"my-sveltekit-app"', f'"{name}"'),
        "pyproject.toml": ('name = "my-python-app"', f'name = "{name}"'),
        "Cargo.toml": ('name = "my-rust-app"', f'name = "{name}"'),
    }

    for filename, (old, new) in replacements.items():
        path = project_dir / filename
        if not path.is_file():
            continue
        changed = _replace_in_file(path, old, new)
        if changed:
            results.append(StepResult(level="success", message=f"Updating {filename}"))
        else:
            results.append(StepResult(level="info", message=f"skip {filename} (no placeholder)"))

    return results
