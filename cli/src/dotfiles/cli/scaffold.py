"""`dotfiles scaffold <recipe> [app-type] <project-path>` command.

Thin presentation layer: parses args, reads today's date, delegates the whole
flow to ScaffoldService in core, renders the returned steps, and maps the
domain ScaffoldError to a non-zero exit. All orchestration lives in
dotfiles.core.scaffold.service.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from typing import Annotated

import typer

from dotfiles.cli.context import app_context
from dotfiles.cli.ui import render_steps
from dotfiles.console import console
from dotfiles.core.scaffold.service import ScaffoldError, ScaffoldPlan, ScaffoldService, build_plan


def _print_header(plan: ScaffoldPlan) -> None:
    verb = "Creating" if plan.is_new else "Updating"
    console.print(f"[bold blue]{verb} {plan.recipe}/{plan.app_type} project: {plan.name}[/]")
    console.print(f"Location: {plan.project_dir}\n")


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

    try:
        plan = build_plan(
            recipe, arg2, arg3, force=force, tools=tools, today=datetime.now().date().isoformat()
        )
    except ScaffoldError as exc:
        console.print(f"[red]✗ {exc}[/]")
        raise typer.Exit(1) from exc

    _print_header(plan)

    # which=shutil.which is passed at call time so tests can monkeypatch it.
    service = ScaffoldService(
        runner=app_ctx.runner, dotfiles_dir=app_ctx.dotfiles_dir, which=shutil.which
    )
    steps = service.run(plan, audit=audit, baselines=baselines, sync=with_agent_rules_sync)

    render_steps(console, steps)
    console.print()

    if any(s.level == "error" for s in steps):
        console.print("[red]✗ Scaffold completed with errors.[/]")
        raise typer.Exit(1)
    console.print("[green]✓ Project scaffolded successfully![/]")
