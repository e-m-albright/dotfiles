"""`dotfiles brew` commands: install packages from packages.toml; report stale."""

from __future__ import annotations

from typing import Annotated

import typer

from dotfiles.app.context import app_context
from dotfiles.cmd.brew.service import (
    PackageManifest,
    add_taps,
    install_claude_code,
    install_hermes,
    install_npm_globals,
    install_packages,
    install_rust,
    install_typewhisper,
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
from dotfiles.result import StepResult

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
    print_title(console, "brew", "install")

    # Taps
    print_section(console, "Taps")
    tap_steps = add_taps(manifest, runner)
    render_steps(console, tap_steps)
    all_steps.extend(tap_steps)

    # Packages
    print_section(console, "Packages")
    pkg_steps = install_packages(manifest, runner, flags_on=flags, dry_run=dry_run)
    render_steps(console, pkg_steps)
    all_steps.extend(pkg_steps)

    if not dry_run:
        # Rust
        print_section(console, "Rust (rustup)")
        rust_steps = install_rust(runner, home=app_ctx.home)
        render_steps(console, rust_steps)
        all_steps.extend(rust_steps)

        # Claude Code + Hermes (ai flag)
        if "ai" in flags:
            print_section(console, "Claude Code")
            cc_steps = install_claude_code(runner)
            render_steps(console, cc_steps)
            all_steps.extend(cc_steps)

            print_section(console, "Hermes")
            hermes_steps = install_hermes(runner)
            render_steps(console, hermes_steps)
            all_steps.extend(hermes_steps)

        # TypeWhisper (productivity flag)
        if "productivity" in flags:
            print_section(console, "TypeWhisper")
            tw_steps = install_typewhisper(runner, dotfiles_dir=app_ctx.dotfiles_dir)
            render_steps(console, tw_steps)
            all_steps.extend(tw_steps)

        # npm globals
        print_section(console, "npm globals")
        npm_steps = install_npm_globals(manifest, runner, flags_on=flags)
        render_steps(console, npm_steps)
        all_steps.extend(npm_steps)

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

    stale_list = stale_packages(manifest, runner)
    missing_list = missing_packages(manifest, runner, flags_on=set(app_ctx.feature_flags))

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
