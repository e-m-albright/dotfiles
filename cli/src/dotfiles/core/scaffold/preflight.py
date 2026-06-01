"""Pre-flight checks for scaffold dependencies.

Faithful port of the check_command() / preflight checks in scaffold.sh.
Warns (does not abort) when a recipe's toolchain is missing.
"""

from __future__ import annotations

from collections.abc import Callable

from dotfiles.core.models import StepResult

# Type alias: a callable that returns True iff the command exists.
WhichFn = Callable[[str], bool]

# ---------------------------------------------------------------------------
# Per-command check
# ---------------------------------------------------------------------------


def check_command(which: WhichFn, cmd: str) -> StepResult:
    """Return a StepResult for whether *cmd* is available.

    Uses *which* (injected) so tests can fake it without touching the OS.
    """
    if which(cmd):
        return StepResult(level="success", message=f"{cmd} found")
    return StepResult(level="warn", message=f"Missing: {cmd}")


# ---------------------------------------------------------------------------
# Per-recipe preflight
# ---------------------------------------------------------------------------

_RECIPE_CMDS: dict[str, list[str]] = {
    "typescript": ["bun"],
    "python": ["uv"],
    "golang": ["go"],
    "rust": ["cargo"],
}

# Always checked regardless of recipe (mirrors scaffold.sh)
_COMMON_CMDS: list[str] = ["git", "curl"]

# Optional — warn-only, never fails preflight (mirrors "|| true" in scaffold.sh)
_OPTIONAL_CMDS: list[str] = ["lefthook"]


def preflight(recipe: str, which: WhichFn) -> list[StepResult]:
    """Run pre-flight checks for *recipe* and return a list of StepResults.

    All checks are warn-not-abort (matching scaffold.sh behaviour).
    Optional tools (lefthook) produce a warn result if missing but are
    included in the returned list so the caller can report them.
    """
    results: list[StepResult] = []

    for cmd in _RECIPE_CMDS.get(recipe, []):
        results.append(check_command(which, cmd))

    for cmd in _COMMON_CMDS:
        results.append(check_command(which, cmd))

    for cmd in _OPTIONAL_CMDS:
        results.append(check_command(which, cmd))

    return results
