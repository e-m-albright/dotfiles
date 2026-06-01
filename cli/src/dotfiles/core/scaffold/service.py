"""ScaffoldService — the orchestration behind `dotfiles scaffold`.

Faithful port of prompts/scaffold.sh's main flow. All heavy per-step logic
lives in the sibling scaffold modules; this service sequences them and owns the
positional-disambiguation rules. Pure with respect to I/O: the clock (`today`)
and `which`/`runner` ports are injected, so the whole flow is unit-testable
without Typer or a real filesystem clock. The CLI layer only parses args,
prints the header, renders the returned steps, and maps ScaffoldError → exit.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dotfiles.core.models import StepResult
from dotfiles.core.ports import ProcessRunner
from dotfiles.core.scaffold.agents_md import write_agents_md
from dotfiles.core.scaffold.artifacts import create_artifacts_dir
from dotfiles.core.scaffold.gitignore import update_gitignore
from dotfiles.core.scaffold.optional_scaffolds import (
    deploy_agent_rules_sync,
    deploy_audit_pipeline,
    deploy_baselines,
)
from dotfiles.core.scaffold.preflight import preflight
from dotfiles.core.scaffold.project_rename import update_project_name
from dotfiles.core.scaffold.recipes import (
    DEFAULT_APP_TYPES,
    VALID_RECIPES,
    get_recipe_rules,
    is_known_app_type,
)
from dotfiles.core.scaffold.rules import copy_ai_rule
from dotfiles.core.scaffold.symlinks import generate_root_symlinks, setup_tool_symlinks
from dotfiles.core.scaffold.templates import copy_template_files
from dotfiles.core.scaffold.tool_registry import ToolTarget, load_registry, tools_for_filter

_WhichFn = Callable[[str], str | None]
_LOWER_RE = "abcdefghijklmnopqrstuvwxyz"


class ScaffoldError(Exception):
    """Invalid scaffold invocation (unknown recipe / app-type, missing path)."""


@dataclass(frozen=True)
class ScaffoldPlan:
    """Resolved scaffold parameters — the disambiguated, path-resolved inputs."""

    recipe: str
    app_type: str
    project_dir: Path
    name: str
    is_new: bool
    force: bool
    tools_filter: str
    today: str


# ---------------------------------------------------------------------------
# Argument resolution (pure)
# ---------------------------------------------------------------------------


def _is_existing_path(arg: str) -> bool:
    """Mirror is_existing_path(): "." or an existing directory."""
    return arg == "." or Path(arg).is_dir()


def _looks_like_app_type(arg: str) -> bool:
    """True iff arg is all-lowercase letters (matches bash ^[a-z]+$)."""
    return len(arg) > 0 and all(c in _LOWER_RE for c in arg)


def resolve_tools_filter(tools: str) -> str:
    """Replicate scaffold.sh's --tools handling.

    Default is "cursor". ``--tools all`` → "all". Otherwise the user's list is
    prepended with "cursor" (always included), matching ``SCAFFOLD_TOOLS="cursor,$2"``.
    """
    if tools == "all":
        return "all"
    if tools == "cursor":
        return "cursor"
    return f"cursor,{tools}"


def disambiguate(recipe: str, arg2: str, arg3: str | None) -> tuple[str, str]:
    """Resolve (app_type, project_path) from the two positionals.

    Faithful port of the 1-arg / 2-arg branching in scaffold.sh. Raises
    ScaffoldError for the missing-path and unknown-app-type cases.
    """
    if arg3 is None:
        if is_known_app_type(recipe, arg2):
            raise ScaffoldError(
                f"Missing project path. Usage: dotfiles scaffold {recipe} {arg2} <project-path>"
            )
        return DEFAULT_APP_TYPES.get(recipe, ""), arg2

    if is_known_app_type(recipe, arg2):
        return arg2, arg3

    # arg2 is not a known app-type — treat it as the project path if it looks
    # like one (existing path, or not a bare lowercase token), else it's an error.
    if _is_existing_path(arg2) or not _looks_like_app_type(arg2):
        return DEFAULT_APP_TYPES.get(recipe, ""), arg2

    raise ScaffoldError(f"Unknown app type '{arg2}' for recipe '{recipe}'")


def build_plan(
    recipe: str,
    arg2: str,
    arg3: str | None,
    *,
    force: bool,
    tools: str,
    today: str,
) -> ScaffoldPlan:
    """Validate the recipe, disambiguate positionals, and resolve the target dir.

    Raises ScaffoldError for an unknown recipe or unresolvable positionals.
    *today* (ISO date) is injected — the core never reads the clock.
    """
    if recipe not in VALID_RECIPES:
        raise ScaffoldError(
            f"Unknown recipe '{recipe}'. Available recipes: {' '.join(VALID_RECIPES)}"
        )

    app_type, project_path_arg = disambiguate(recipe, arg2, arg3)

    if project_path_arg == ".":
        project_dir = Path.cwd()
        is_new = False
    else:
        project_dir = Path(project_path_arg).expanduser().resolve()
        is_new = not project_dir.is_dir()

    return ScaffoldPlan(
        recipe=recipe,
        app_type=app_type,
        project_dir=project_dir,
        name=project_dir.name,
        is_new=is_new,
        force=force,
        tools_filter=resolve_tools_filter(tools),
        today=today,
    )


def gitignore_entries(registry: dict[str, ToolTarget], tools_filter: str) -> list[str]:
    """Build the tool-rules .gitignore lines (rule dirs + root symlinks)."""
    entries: list[str] = []

    def _selected(tool: str) -> bool:
        return tools_filter == "all" or tool in tools_filter.split(",")

    if _selected("cursor"):
        entries.append(".cursor/rules/")
    if _selected("copilot"):
        entries.append(".github/instructions/")
    if _selected("gemini"):
        entries.append(".gemini/rules/")

    for name, target in registry.items():
        if target.root_file is None:
            continue
        if tools_filter == "all" or name in tools_filter.split(","):
            entries.append(target.root_file)

    return entries


def root_symlink_tools(registry: dict[str, ToolTarget], tools_filter: str) -> dict[str, ToolTarget]:
    """Registry subset for root symlinks: rootFile != null, honoring the filter."""
    if tools_filter == "all":
        return {k: v for k, v in registry.items() if v.root_file is not None}
    requested = {n.strip() for n in tools_filter.split(",") if n.strip()}
    return {k: v for k, v in registry.items() if v.root_file is not None and k in requested}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ScaffoldService:
    """Sequence the scaffold steps for a resolved ScaffoldPlan."""

    def __init__(
        self,
        *,
        runner: ProcessRunner,
        dotfiles_dir: Path,
        which: _WhichFn = shutil.which,
    ) -> None:
        self._runner = runner
        self._dotfiles = dotfiles_dir
        self._which = which

    def _has(self, cmd: str) -> bool:
        return self._which(cmd) is not None

    def run(
        self,
        plan: ScaffoldPlan,
        *,
        audit: bool = False,
        baselines: bool = False,
        sync: bool = False,
    ) -> list[StepResult]:
        """Full scaffold flow. Returns every step (preflight warnings first).

        If git is required but missing, returns the warnings plus a single error
        step and makes no filesystem changes (abort-before-mutate).
        """
        steps = self._preflight_warnings(plan.recipe)

        needs_git_init = not (plan.project_dir / ".git").is_dir()
        if needs_git_init and not self._has("git"):
            steps.append(
                StepResult(level="error", message="git is required to scaffold a new project")
            )
            return steps

        steps.extend(self._scaffold_files(plan))
        steps.extend(self._deploy_optionals(plan, audit=audit, baselines=baselines, sync=sync))
        steps.extend(self._git_and_hooks(plan))
        return steps

    def _preflight_warnings(self, recipe: str) -> list[StepResult]:
        """Warn-only toolchain checks (matching scaffold.sh)."""
        return [s for s in preflight(recipe, self._has) if s.level == "warn"]

    def _scaffold_files(self, plan: ScaffoldPlan) -> list[StepResult]:
        """Create dirs, copy rules/templates, set up symlinks, AGENTS.md, gitignore."""
        steps: list[StepResult] = []

        if plan.is_new:
            plan.project_dir.mkdir(parents=True, exist_ok=True)
            steps.append(
                copy_template_files(self._dotfiles, plan.project_dir, plan.recipe, plan.app_type)
            )

        for rule_path in get_recipe_rules(plan.recipe, plan.app_type):
            steps.append(
                copy_ai_rule(
                    self._dotfiles, plan.project_dir, rule_path, force=plan.force, today=plan.today
                )
            )

        registry = load_registry(self._dotfiles)
        symlink_tools = tools_for_filter(registry, plan.tools_filter, strategy="symlink")
        setup_tool_symlinks(plan.project_dir, symlink_tools, force=plan.force)

        # Match scaffold.sh order: AGENTS.md before root symlinks point at it.
        steps.append(write_agents_md(plan.project_dir, plan.name, force=plan.force))

        for root in generate_root_symlinks(
            plan.project_dir, root_symlink_tools(registry, plan.tools_filter), force=plan.force
        ):
            steps.append(StepResult(level="success", message=f"Linked {root} → AGENTS.md"))

        create_artifacts_dir(plan.project_dir)
        steps.append(StepResult(level="info", message=".ai/artifacts/ ready"))

        for section in update_gitignore(
            plan.project_dir, gitignore_entries(registry, plan.tools_filter)
        ):
            steps.append(StepResult(level="success", message=f"Added {section} to .gitignore"))

        if plan.is_new:
            steps.extend(update_project_name(plan.project_dir, plan.name))

        return steps

    def _deploy_optionals(
        self, plan: ScaffoldPlan, *, audit: bool, baselines: bool, sync: bool
    ) -> list[StepResult]:
        """Deploy the opt-in scaffold bundles selected by --with-* flags."""
        steps: list[StepResult] = []
        if audit:
            steps.extend(deploy_audit_pipeline(self._dotfiles, plan.project_dir, force=plan.force))
        if baselines:
            steps.extend(deploy_baselines(self._dotfiles, plan.project_dir, force=plan.force))
        if sync:
            steps.extend(
                deploy_agent_rules_sync(self._dotfiles, plan.project_dir, force=plan.force)
            )
        return steps

    def _git_and_hooks(self, plan: ScaffoldPlan) -> list[StepResult]:
        """git init (+ initial commit for new projects) and lefthook install."""
        steps: list[StepResult] = []
        proj = str(plan.project_dir)

        if not (plan.project_dir / ".git").is_dir():
            self._runner.run(["git", "-C", proj, "init", "-q"])
            steps.append(StepResult(level="success", message="Initializing git repository"))
            if plan.is_new:
                self._runner.run(["git", "-C", proj, "add", "-A"])
                message = (
                    f"Initial project setup from {plan.recipe}/{plan.app_type} recipe\n\n"
                    f"Generated from dotfiles/prompts/{plan.recipe}/{plan.app_type}"
                )
                self._runner.run(["git", "-C", proj, "commit", "-q", "-m", message])

        if (plan.project_dir / "lefthook.yml").is_file() and self._has("lefthook"):
            self._runner.run(["lefthook", "install"])
            steps.append(StepResult(level="success", message="Installing git hooks (lefthook)"))

        return steps
