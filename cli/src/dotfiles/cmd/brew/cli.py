"""`dotfiles brew` commands: install packages from packages.toml; report stale."""

from __future__ import annotations

from typing import Annotated

import typer

from dotfiles.app.context import app_context
from dotfiles.app.fuzzy import FuzzyTyperGroup
from dotfiles.cmd.brew.service import (
    ALL_FLAGS,
    BrewInventoryError,
    FeatureFlag,
    InstallPlan,
    PackageManifest,
    cleanup,
    go_drift,
    install_software,
    npm_drift,
    stale_taps,
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


def _flags_on(*, no_ai: bool, no_productivity: bool, no_social: bool) -> set[FeatureFlag]:
    """All feature flags minus the per-run --no-* overrides."""
    disabled: dict[FeatureFlag, bool] = {
        "ai": no_ai,
        "productivity": no_productivity,
        "social": no_social,
    }
    return {flag for flag in ALL_FLAGS if not disabled[flag]}


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
    flags = _flags_on(no_ai=no_ai, no_productivity=no_productivity, no_social=no_social)
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


def clean_command(ctx: typer.Context) -> None:
    """Clean Homebrew caches."""
    app_ctx = app_context(ctx)
    print_title(console, "clean")
    print_section(console, "Homebrew")
    steps = cleanup(app_ctx.runner)
    render_steps(console, steps)
    console.print()
    if has_errors(steps):
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


def _render_stale_items(title: str, subtitle: str, items: list[str], command: str) -> None:
    print_section(console, title, subtitle)
    if not items:
        print_status(console, "success", "none")
        return
    for name in items:
        console.print(f"  [yellow]⚠[/] {name}  [dim]{command} {name}[/]")


@brew_app.command()
def stale(ctx: typer.Context) -> None:
    """Report installed packages not declared in packages.toml (stale) and missing ones."""
    app_ctx = app_context(ctx)
    manifest = _manifest(ctx)
    runner = app_ctx.runner

    try:
        # One inventory pass covers both lists (stale is flag-independent).
        plan = InstallPlan.compute(manifest, runner, flags_on=ALL_FLAGS)
        stale_list = plan.stale
        stale_tap_list = stale_taps(manifest, runner)
        missing_list = plan.missing
        npm_drift_list = npm_drift(manifest, runner)
        go_drift_list = go_drift(manifest, runner)
    except BrewInventoryError as exc:
        print_status(console, "error", str(exc))
        raise typer.Exit(code=1) from exc

    print_title(console, "brew", "stale")
    _render_stale_items(
        "Stale packages", "installed but not declared", stale_list, "brew uninstall"
    )
    _render_stale_items("Stale taps", "installed but not declared", stale_tap_list, "brew untap")

    print_section(console, "Missing packages", "declared but not installed")
    if missing_list:
        for name, kind in missing_list:
            console.print(f"  [red]✗[/] {name}  [dim]({kind})[/]")
    else:
        print_status(console, "success", "none")

    print_section(console, "npm / go drift", "declared but missing or version-drifted")
    drift = npm_drift_list + go_drift_list
    if drift:
        for item in drift:
            console.print(f"  [red]✗[/] {item}")
        console.print("  [dim]Heal with: dotfiles brew install[/]")
    else:
        print_status(console, "success", "none")

    console.print()
