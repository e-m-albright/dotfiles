"""`dotfiles brew` commands: install packages from packages.toml; report stale."""

from __future__ import annotations

from typing import Annotated

import typer

from dotfiles.cli.context import app_context
from dotfiles.cli.ui import has_errors, render_steps
from dotfiles.console import console
from dotfiles.core.brew import (
    PackageManifest,
    add_taps,
    install_claude_code,
    install_npm_globals,
    install_packages,
    install_rust,
    install_typewhisper,
    missing_packages,
    stale_packages,
)
from dotfiles.core.models import StepResult

brew_app = typer.Typer(help="Manage Homebrew packages from packages.toml.")


def _manifest(ctx: typer.Context) -> PackageManifest:
    app_ctx = app_context(ctx)
    toml_path = app_ctx.dotfiles_dir / "macos" / "packages.toml"
    return PackageManifest.load(toml_path)


def _flags_on(
    env_flags: frozenset[str], *, no_ai: bool, no_productivity: bool, no_social: bool
) -> set[str]:
    """Intersect the env-enabled feature flags with the per-run --no-* overrides."""
    disabled = {"ai": no_ai, "productivity": no_productivity, "social": no_social}
    return {flag for flag in env_flags if not disabled.get(flag, False)}


@brew_app.command()
def install(
    ctx: typer.Context,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Report what would be installed; run nothing.")
    ] = False,
    no_ai: Annotated[bool, typer.Option("--no-ai", help="Skip ai-flagged packages.")] = False,
    no_productivity: Annotated[
        bool, typer.Option("--no-productivity", help="Skip productivity-flagged packages.")
    ] = False,
    no_social: Annotated[
        bool, typer.Option("--no-social", help="Skip social-flagged packages.")
    ] = False,
) -> None:
    """Install all packages declared in packages.toml (idempotent)."""
    app_ctx = app_context(ctx)
    manifest = _manifest(ctx)
    flags = _flags_on(
        app_ctx.feature_flags, no_ai=no_ai, no_productivity=no_productivity, no_social=no_social
    )
    runner = app_ctx.runner

    all_steps: list[StepResult] = []

    # Taps
    console.print("\n[bold blue]Taps[/]")
    tap_steps = add_taps(manifest, runner)
    render_steps(console, tap_steps)
    all_steps.extend(tap_steps)

    # Packages
    console.print("\n[bold blue]Packages[/]")
    pkg_steps = install_packages(manifest, runner, flags_on=flags, dry_run=dry_run)
    render_steps(console, pkg_steps)
    all_steps.extend(pkg_steps)

    if not dry_run:
        # Rust
        console.print("\n[bold blue]Rust (rustup)[/]")
        rust_steps = install_rust(runner, home=app_ctx.home)
        render_steps(console, rust_steps)
        all_steps.extend(rust_steps)

        # Claude Code (ai flag)
        if "ai" in flags:
            console.print("\n[bold blue]Claude Code[/]")
            cc_steps = install_claude_code(runner)
            render_steps(console, cc_steps)
            all_steps.extend(cc_steps)

        # TypeWhisper (productivity flag)
        if "productivity" in flags:
            console.print("\n[bold blue]TypeWhisper[/]")
            tw_steps = install_typewhisper(runner)
            render_steps(console, tw_steps)
            all_steps.extend(tw_steps)

        # npm globals
        console.print("\n[bold blue]npm globals[/]")
        npm_steps = install_npm_globals(manifest, runner, flags_on=flags)
        render_steps(console, npm_steps)
        all_steps.extend(npm_steps)

    console.print()
    if has_errors(all_steps):
        raise typer.Exit(code=1)


@brew_app.command()
def stale(ctx: typer.Context) -> None:
    """Report installed packages not declared in packages.toml (stale) and missing ones."""
    app_ctx = app_context(ctx)
    manifest = _manifest(ctx)
    runner = app_ctx.runner

    stale_list = stale_packages(manifest, runner)
    missing_list = missing_packages(manifest, runner, flags_on=set(app_ctx.feature_flags))

    console.print("\n[bold blue]Stale packages[/] (installed but not declared)")
    if stale_list:
        for name in stale_list:
            console.print(f"  [yellow]○[/] {name}  [dim]brew uninstall {name}[/]")
    else:
        console.print("  [green]✓[/] None")

    console.print("\n[bold blue]Missing packages[/] (declared but not installed)")
    if missing_list:
        for name, kind in missing_list:
            console.print(f"  [red]✗[/] {name}  [dim]({kind})[/]")
    else:
        console.print("  [green]✓[/] None")

    console.print()
