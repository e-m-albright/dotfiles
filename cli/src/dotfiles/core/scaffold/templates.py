"""Copy template files for new projects.

Faithful port of the template-copy block in scaffold.sh.
Copies from prompts/<recipe>/<app_type>/templates/ (preferred)
or prompts/<recipe>/templates/ (fallback) into *project_dir*.
Only runs for new projects (caller's responsibility to gate on is_new).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from dotfiles.core.models import StepResult


def copy_template_files(
    dotfiles_dir: Path,
    project_dir: Path,
    recipe: str,
    app_type: str,
) -> StepResult:
    """Copy template files from the dotfiles prompts tree into *project_dir*.

    Tries the app-type-specific template dir first, then the recipe-level
    fallback — mirroring scaffold.sh's two-tier lookup.

    Returns a StepResult describing what happened (or info/skip if no
    template dir was found).
    """
    prompts_dir = dotfiles_dir / "prompts"
    app_template_dir = prompts_dir / recipe / app_type / "templates"
    recipe_template_dir = prompts_dir / recipe / "templates"

    if app_template_dir.is_dir():
        src_dir = app_template_dir
        label = f"from {app_type}"
    elif recipe_template_dir.is_dir():
        src_dir = recipe_template_dir
        label = "from recipe"
    else:
        return StepResult(level="info", message=f"No template dir for {recipe}/{app_type}")

    # Copy all contents (including hidden files) — mirrors cp -r .../templates/* and .*
    for item in src_dir.iterdir():
        dest = project_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    return StepResult(level="success", message=f"Copying template files ({label})")
