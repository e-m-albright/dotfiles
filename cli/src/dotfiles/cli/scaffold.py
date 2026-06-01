"""`dotfiles scaffold <recipe> [app-type] <project-path>` command.

Faithful port of prompts/scaffold.sh: creates or updates a project with
cross-vendor AI rules.  All heavy logic lives in dotfiles.core.scaffold; this
module handles arg parsing, positional disambiguation, orchestration order,
and rendering.

Isolation contract: writes only to the resolved project-path argument.  Today's
date is read here (at the CLI layer) and passed down — core never reads the clock.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from dotfiles.cli.context import app_context
from dotfiles.cli.ui import render_steps
from dotfiles.console import console
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

_LOWER_RE = "abcdefghijklmnopqrstuvwxyz"


def _is_existing_path(arg: str) -> bool:
    """Mirror is_existing_path(): "." or an existing directory."""
    return arg == "." or Path(arg).is_dir()


def _looks_like_app_type(arg: str) -> bool:
    """True iff arg is all-lowercase letters (matches bash ^[a-z]+$)."""
    return len(arg) > 0 and all(c in _LOWER_RE for c in arg)


def _resolve_tools_filter(tools: str) -> str:
    """Replicate scaffold.sh's --tools handling.

    Default is "cursor".  ``--tools all`` → "all".  Otherwise the user's list
    is prepended with "cursor" (so cursor is always included), matching
    ``SCAFFOLD_TOOLS="cursor,$2"``.
    """
    if tools == "all":
        return "all"
    if tools == "cursor":
        return "cursor"
    return f"cursor,{tools}"


def _gitignore_entries(
    registry: dict[str, ToolTarget],
    tools_filter: str,
) -> list[str]:
    """Build the tool-rules .gitignore lines (rule dirs + root symlinks).

    Mirrors the update_gitignore block in scaffold.sh: a hardcoded rule-dir
    line per known tool when selected, plus every rootFile for selected tools.
    """
    entries: list[str] = []

    def _selected(tool: str) -> bool:
        return tools_filter == "all" or tool in tools_filter.split(",")

    if _selected("cursor"):
        entries.append(".cursor/rules/")
    if _selected("copilot"):
        entries.append(".github/instructions/")
    if _selected("gemini"):
        entries.append(".gemini/rules/")

    # Root symlinks to AGENTS.md (CODEX.md, GEMINI.md, ...)
    for name, target in registry.items():
        if target.root_file is None:
            continue
        if tools_filter == "all" or name in tools_filter.split(","):
            entries.append(target.root_file)

    return entries


def _root_symlink_tools(
    registry: dict[str, ToolTarget],
    tools_filter: str,
) -> dict[str, ToolTarget]:
    """Registry subset for root symlinks: rootFile != null, honoring the filter.

    Unlike tools_for_filter (which constrains by strategy), the scaffold.sh
    root-symlink jq query selects on rootFile alone.
    """
    if tools_filter == "all":
        return {k: v for k, v in registry.items() if v.root_file is not None}
    requested = {n.strip() for n in tools_filter.split(",") if n.strip()}
    return {k: v for k, v in registry.items() if v.root_file is not None and k in requested}


@dataclass(frozen=True)
class _Plan:
    """Resolved scaffold parameters — the disambiguated, path-resolved inputs."""

    recipe: str
    app_type: str
    project_dir: Path
    name: str
    is_new: bool
    force: bool
    tools_filter: str
    today: str


def _build_plan(
    recipe: str,
    arg2: str,
    arg3: str | None,
    *,
    force: bool,
    tools: str,
) -> _Plan:
    """Disambiguate positionals and resolve the target project dir into a _Plan."""
    app_type, project_path_arg = _disambiguate(recipe, arg2, arg3)

    if project_path_arg == ".":
        project_dir = Path.cwd()
        is_new = False
    else:
        project_dir = Path(project_path_arg).expanduser().resolve()
        is_new = not project_dir.is_dir()

    return _Plan(
        recipe=recipe,
        app_type=app_type,
        project_dir=project_dir,
        name=project_dir.name,
        is_new=is_new,
        force=force,
        tools_filter=_resolve_tools_filter(tools),
        today=datetime.now().date().isoformat(),
    )


def scaffold_command(
    ctx: typer.Context,
    recipe: Annotated[
        str,
        typer.Argument(help="Recipe: typescript, python, golang, rust."),
    ],
    arg2: Annotated[
        str,
        typer.Argument(
            metavar="[APP-TYPE] PROJECT-PATH",
            help="App-type (then project-path follows) or the project-path itself.",
        ),
    ],
    arg3: Annotated[
        str | None,
        typer.Argument(metavar="[PROJECT-PATH]", help="Project path (when app-type given)."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Force regenerate AGENTS.md and overwrite existing rules."),
    ] = False,
    tools: Annotated[
        str,
        typer.Option(
            "--tools",
            help="Comma-separated tools for symlinks (or 'all'). Default: cursor.",
        ),
    ] = "cursor",
    with_audit_pipeline: Annotated[
        bool,
        typer.Option("--with-audit-pipeline", help="Deploy scripts/audit/ + just/audit/."),
    ] = False,
    with_baselines: Annotated[
        bool,
        typer.Option("--with-baselines", help="Deploy baselines.json code-health ratchet."),
    ] = False,
    with_code_health: Annotated[
        bool,
        typer.Option("--with-code-health", help="Shorthand for audit-pipeline + baselines."),
    ] = False,
    with_agent_rules_sync: Annotated[
        bool,
        typer.Option("--with-agent-rules-sync", help="Deploy sync-agent-rules.sh fragment."),
    ] = False,
) -> None:
    """Scaffold or update a project with cross-vendor AI rules."""
    app_ctx = app_context(ctx)

    # --with-code-health is shorthand for both
    audit = with_audit_pipeline or with_code_health
    baselines = with_baselines or with_code_health

    if recipe not in VALID_RECIPES:
        console.print(f"[red]✗ Unknown recipe '{recipe}'[/]")
        console.print(f"Available recipes: {' '.join(VALID_RECIPES)}")
        raise typer.Exit(1)

    plan = _build_plan(recipe, arg2, arg3, force=force, tools=tools)
    _print_header(plan)

    def _which(cmd: str) -> bool:
        return shutil.which(cmd) is not None

    # Pre-flight is warn-only (matching scaffold.sh).
    pf = preflight(recipe, _which)
    render_steps(console, [s for s in pf if s.level == "warn"])

    # git is the one hard requirement: a new project's git init is core to
    # scaffolding, so fail fast with a clear message rather than a confusing
    # subprocess error mid-way. (Recipe toolchains stay warn-not-abort above.)
    _require_git(plan, _which)

    steps = _scaffold_files(app_ctx.dotfiles_dir, plan)
    steps.extend(
        _deploy_optionals(
            app_ctx.dotfiles_dir, plan, audit=audit, baselines=baselines, sync=with_agent_rules_sync
        )
    )
    steps.extend(_git_and_hooks(app_ctx.runner, plan))

    render_steps(console, steps)
    console.print()

    if any(s.level == "error" for s in steps):
        console.print("[red]✗ Scaffold completed with errors.[/]")
        raise typer.Exit(1)
    console.print("[green]✓ Project scaffolded successfully![/]")


def _print_header(plan: _Plan) -> None:
    verb = "Creating" if plan.is_new else "Updating"
    console.print(f"[bold blue]{verb} {plan.recipe}/{plan.app_type} project: {plan.name}[/]")
    console.print(f"Location: {plan.project_dir}\n")


def _scaffold_files(dotfiles_dir: Path, plan: _Plan) -> list[StepResult]:
    """Create dirs, copy rules/templates, set up symlinks, AGENTS.md, gitignore."""
    steps: list[StepResult] = []

    if plan.is_new:
        plan.project_dir.mkdir(parents=True, exist_ok=True)
        steps.append(
            copy_template_files(dotfiles_dir, plan.project_dir, plan.recipe, plan.app_type)
        )

    for rule_path in get_recipe_rules(plan.recipe, plan.app_type):
        steps.append(
            copy_ai_rule(
                dotfiles_dir, plan.project_dir, rule_path, force=plan.force, today=plan.today
            )
        )

    registry = load_registry(dotfiles_dir)
    symlink_tools = tools_for_filter(registry, plan.tools_filter, strategy="symlink")
    setup_tool_symlinks(plan.project_dir, symlink_tools, force=plan.force)

    # Match scaffold.sh order: AGENTS.md is written before root symlinks point
    # at it (setup_tool_symlinks → write_agents_md → generate_root_symlinks).
    steps.append(write_agents_md(plan.project_dir, plan.name, force=plan.force))

    for root in generate_root_symlinks(
        plan.project_dir, _root_symlink_tools(registry, plan.tools_filter), force=plan.force
    ):
        steps.append(StepResult(level="success", message=f"Linked {root} → AGENTS.md"))

    create_artifacts_dir(plan.project_dir)
    steps.append(StepResult(level="info", message=".ai/artifacts/ ready"))

    entries = _gitignore_entries(registry, plan.tools_filter)
    for section in update_gitignore(plan.project_dir, entries):
        steps.append(StepResult(level="success", message=f"Added {section} to .gitignore"))

    if plan.is_new:
        steps.extend(update_project_name(plan.project_dir, plan.name))

    return steps


def _deploy_optionals(
    dotfiles_dir: Path,
    plan: _Plan,
    *,
    audit: bool,
    baselines: bool,
    sync: bool,
) -> list[StepResult]:
    """Deploy the opt-in scaffold bundles selected by --with-* flags."""
    steps: list[StepResult] = []
    if audit:
        steps.extend(deploy_audit_pipeline(dotfiles_dir, plan.project_dir, force=plan.force))
    if baselines:
        steps.extend(deploy_baselines(dotfiles_dir, plan.project_dir, force=plan.force))
    if sync:
        steps.extend(deploy_agent_rules_sync(dotfiles_dir, plan.project_dir, force=plan.force))
    return steps


def _require_git(plan: _Plan, which: Callable[[str], bool]) -> None:
    """Hard-fail before scaffolding if git is needed but unavailable.

    A project without a `.git` dir will be `git init`-ed by _git_and_hooks; if
    git is missing that would blow up with an opaque subprocess error. Emit a
    clear error StepResult and exit 1 *before* any filesystem changes.
    """
    needs_git_init = not (plan.project_dir / ".git").is_dir()
    if needs_git_init and not which("git"):
        render_steps(
            console,
            [StepResult(level="error", message="git is required to scaffold a new project")],
        )
        raise typer.Exit(1)


def _git_and_hooks(runner: ProcessRunner, plan: _Plan) -> list[StepResult]:
    """git init (+ initial commit for new projects) and lefthook install."""
    steps: list[StepResult] = []
    proj = str(plan.project_dir)

    if not (plan.project_dir / ".git").is_dir():
        runner.run(["git", "-C", proj, "init", "-q"])
        steps.append(StepResult(level="success", message="Initializing git repository"))
        if plan.is_new:
            runner.run(["git", "-C", proj, "add", "-A"])
            message = (
                f"Initial project setup from {plan.recipe}/{plan.app_type} recipe\n\n"
                f"Generated from dotfiles/prompts/{plan.recipe}/{plan.app_type}"
            )
            runner.run(["git", "-C", proj, "commit", "-q", "-m", message])

    if (plan.project_dir / "lefthook.yml").is_file() and shutil.which("lefthook"):
        runner.run(["lefthook", "install"])
        steps.append(StepResult(level="success", message="Installing git hooks (lefthook)"))

    return steps


def _disambiguate(recipe: str, arg2: str, arg3: str | None) -> tuple[str, str]:
    """Resolve (app_type, project_path) from the two positionals.

    Faithful port of the 1-arg / 2-arg branching in scaffold.sh (lines 447-481).
    Typer guarantees arg2 is present (>= 1 positional after recipe).
    """
    if arg3 is None:
        # Exactly one positional after recipe.
        if is_known_app_type(recipe, arg2):
            # It names an app-type but no project path was given.
            raise typer.BadParameter(
                f"Missing project path. Usage: dotfiles scaffold {recipe} {arg2} <project-path>"
            )
        return DEFAULT_APP_TYPES.get(recipe, ""), arg2

    # Two positionals after recipe.
    if is_known_app_type(recipe, arg2):
        return arg2, arg3

    # arg2 is not a known app-type — treat it as the project path if it looks
    # like one (existing path, or not a bare lowercase token), else it's an error.
    if _is_existing_path(arg2) or not _looks_like_app_type(arg2):
        return DEFAULT_APP_TYPES.get(recipe, ""), arg2

    raise typer.BadParameter(f"Unknown app type '{arg2}' for recipe '{recipe}'")
