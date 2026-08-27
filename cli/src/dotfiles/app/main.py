"""Top-level Typer application and command registration."""

from __future__ import annotations

import os
from pathlib import Path

import typer
from typer._click.core import Context
from typer._click.formatting import HelpFormatter
from typer.core import TyperGroup

from dotfiles.app.context import build_real_context
from dotfiles.banner import print_banner
from dotfiles.cmd.brew.cli import brew_app, clean_command
from dotfiles.cmd.doctor.cli import doctor_command
from dotfiles.cmd.password.cli import password_command
from dotfiles.cmd.remote.cli import remote_app

PANEL_MACHINE = "Machine — setup, maintenance, and machine-state"
PANEL_CONTROL = "Control — phone access and utilities"

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SHIM = _REPO_ROOT / "bin" / "dotfiles"
_PASSTHROUGH = {"allow_extra_args": True, "ignore_unknown_options": True}


class BrandedGroup(TyperGroup):
    """Add the wordmark, then delegate help rendering entirely to Typer."""

    def format_help(self, ctx: Context, formatter: HelpFormatter) -> None:
        print_banner()
        super().format_help(ctx, formatter)


app = typer.Typer(
    cls=BrandedGroup,
    name="dotfiles",
    help="Curated Mac dev environment: machine setup, remote control, and utilities.",
    no_args_is_help=True,
    add_completion=False,
)


def _delegate_to_shim(name: str, args: list[str]) -> None:
    """Hand Bash-native commands back to the repository shim."""
    os.execvp(str(_SHIM), [str(_SHIM), name, *args])


@app.callback()
def _main(ctx: typer.Context) -> None:  # type: ignore[reportUnusedFunction]
    """Build the composition context once if a test has not injected one."""
    if ctx.obj is None:
        ctx.obj = build_real_context()


@app.command(rich_help_panel=PANEL_MACHINE, context_settings=_PASSTHROUGH)
def install(ctx: typer.Context) -> None:
    """Run full dotfiles setup."""
    _delegate_to_shim("install", ctx.args)


@app.command(rich_help_panel=PANEL_MACHINE, context_settings=_PASSTHROUGH)
def update(ctx: typer.Context) -> None:
    """Update OS, Homebrew, runtimes, and dev tools."""
    _delegate_to_shim("update", ctx.args)


app.command("doctor", rich_help_panel=PANEL_MACHINE)(doctor_command)
app.add_typer(brew_app, name="brew", rich_help_panel=PANEL_MACHINE)
app.command("clean", rich_help_panel=PANEL_MACHINE)(clean_command)


@app.command(rich_help_panel=PANEL_MACHINE, context_settings=_PASSTHROUGH)
def dock(ctx: typer.Context) -> None:
    """Reset the macOS Dock layout."""
    _delegate_to_shim("dock", ctx.args)


@app.command("profile-shell", rich_help_panel=PANEL_MACHINE, context_settings=_PASSTHROUGH)
def profile_shell(ctx: typer.Context) -> None:
    """Profile shell startup time."""
    _delegate_to_shim("profile-shell", ctx.args)


app.add_typer(remote_app, name="remote", rich_help_panel=PANEL_CONTROL)
app.command("password", rich_help_panel=PANEL_CONTROL)(password_command)


if __name__ == "__main__":  # pragma: no cover
    app(prog_name="dotfiles")
