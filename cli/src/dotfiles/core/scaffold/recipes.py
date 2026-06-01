"""Recipe → rule mappings, app-type defaults, and known combo table.

Faithful port of the get_recipe_rules / get_default_app_type / is_known_app_type
functions in prompts/scaffold.sh.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Recipe → rule paths
# ---------------------------------------------------------------------------

# Map (recipe, app_type) → list of .ai/rules/<path> to copy.
# The lists include both the language/stack rules and the framework rule (if any).
RECIPE_RULES: dict[str, list[str]] = {
    "typescript": [
        "languages/typescript.mdc",
        "tooling/stack-typescript.mdc",
        "tooling/services.mdc",
    ],
    "python": [
        "languages/python.mdc",
        "tooling/stack-python.mdc",
        "tooling/services.mdc",
        "process/shell-automation.mdc",
    ],
    "golang": [
        "languages/golang.mdc",
        "tooling/stack-golang.mdc",
        "tooling/services.mdc",
        "process/shell-automation.mdc",
    ],
    "rust": [
        "languages/rust.mdc",
        "tooling/stack-rust.mdc",
        "tooling/services.mdc",
        "process/shell-automation.mdc",
    ],
}

# Framework rule for each known (recipe, app_type) combo.
# Entries with None mean "no framework rule" (e.g., python/cli).
_FRAMEWORK_RULES: dict[tuple[str, str], str | None] = {
    ("typescript", "svelte"): "frameworks/sveltekit.mdc",
    ("typescript", "astro"): "frameworks/astro.mdc",
    ("python", "fastapi"): "frameworks/fastapi.mdc",
    ("python", "cli"): None,
    ("golang", "chi"): "frameworks/chi.mdc",
    ("rust", "axum"): "frameworks/axum.mdc",
    ("rust", "tauri"): "frameworks/tauri.mdc",
}

# Default app-type per recipe (matches scaffold.sh get_default_app_type).
DEFAULT_APP_TYPES: dict[str, str] = {
    "typescript": "svelte",
    "python": "fastapi",
    "golang": "chi",
    "rust": "axum",
}

VALID_RECIPES: tuple[str, ...] = ("typescript", "python", "golang", "rust")


def get_recipe_rules(recipe: str, app_type: str) -> list[str]:
    """Return the list of rule paths for a recipe + app_type combination.

    Mirrors get_recipe_rules() in scaffold.sh: language/stack rules first,
    then the framework rule (if any).  Returns an empty list for unknown recipes.
    """
    base = list(RECIPE_RULES.get(recipe, []))
    framework = _FRAMEWORK_RULES.get((recipe, app_type))
    if framework is not None:
        base.append(framework)
    return base


def is_known_app_type(recipe: str, app_type: str) -> bool:
    """Return True iff the (recipe, app_type) combo is in the known table.

    Mirrors is_known_app_type() in scaffold.sh.
    """
    return (recipe, app_type) in _FRAMEWORK_RULES
