"""`dotfiles brew` commands: install packages from packages.toml; report stale."""

from __future__ import annotations

from typing import Annotated

import typer

from dotfiles.app.context import app_context
from dotfiles.app.fuzzy import FuzzyTyperGroup
from dotfiles.cmd.brew.service import (
    BrewInventoryError,
    FeatureFlag,
    PackageManifest,
    install_software,
    missing_packages,
    stale_packages,
)
from dotfiles.cmd.brew.service import upgrade as upgrade_packages
from dotfiles.console import (
    console,
    has_errors,
    print_section,
    print_status,
    print_title,
    render_steps,
)

brew_app = typer.Typer(cls=FuzzyTyperGroup, help="Manage Homebrew packages from packages.toml.")


def _manifest(ctx: typer.Context) -> PackageManifest:
    app_ctx = app_context(ctx)
    toml_path = app_ctx.dotfiles_dir / "macos" / "packages.toml"
    return PackageManifest.load(toml_path)


def _flags_on(
    defaults: set[FeatureFlag],
    env_flags: frozenset[FeatureFlag],
    *,
    no_ai: bool,
    no_productivity: bool,
    no_social: bool,
) -> set[FeatureFlag]:
    """Apply environment and per-run overrides to manifest defaults."""
    disabled = {"ai": no_ai, "productivity": no_productivity, "social": no_social}
    return {flag for flag in defaults & env_flags if not disabled[flag]}


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
        manifest.flags.enabled(),
        app_ctx.feature_flags,
        no_ai=no_ai,
        no_productivity=no_productivity,
        no_social=no_social,
    )
    runner = app_ctx.runner

    print_title(console, "brew", "install")
    print_section(console, "Software")
    try:
        all_steps = install_software(
            manifest,
            runner,
            flags_on=flags,
            dotfiles_dir=app_ctx.dotfiles_dir,
            dry_run=dry_run,
        )
    except BrewInventoryError as exc:
        print_status(console, "error", str(exc))
        raise typer.Exit(code=1) from exc
    render_steps(console, all_steps)

    console.print()
    if has_errors(all_steps):
        raise typer.Exit(code=1)


@brew_app.command()
def upgrade(ctx: typer.Context) -> None:
    """Upgrade all installed packages (brew is the only version-pinning surface)."""
    app_ctx = app_context(ctx)
    print_title(console, "brew", "upgrade")
    print_section(console, "Upgrading Homebrew packages")
    steps = upgrade_packages(app_ctx.runner)
    render_steps(console, steps)
    console.print()
    if has_errors(steps):
        raise typer.Exit(code=1)


@brew_app.command()
def stale(ctx: typer.Context) -> None:
    """Report installed packages not declared in packages.toml (stale) and missing ones."""
    app_ctx = app_context(ctx)
    manifest = _manifest(ctx)
    runner = app_ctx.runner

    try:
        stale_list = stale_packages(manifest, runner)
        missing_list = missing_packages(
            manifest, runner, flags_on=manifest.flags.enabled() & set(app_ctx.feature_flags)
        )
    except BrewInventoryError as exc:
        print_status(console, "error", str(exc))
        raise typer.Exit(code=1) from exc

    print_title(console, "brew", "stale")
    print_section(console, "Stale packages", "installed but not declared")
    if stale_list:
        for name in stale_list:
            console.print(f"  [yellow]⚠[/] {name}  [dim]brew uninstall {name}[/]")
    else:
        print_status(console, "success", "none")

    print_section(console, "Missing packages", "declared but not installed")
    if missing_list:
        for name, kind in missing_list:
            console.print(f"  [red]✗[/] {name}  [dim]({kind})[/]")
    else:
        print_status(console, "success", "none")

    console.print()
