"""Top-level Typer application. Subcommands are mounted here; logic lives in core.

The whole command tree — including the handful of commands still implemented in
the bash shim — is registered here so a single renderer (Typer + Rich) draws both
`dotfiles --help` and every `dotfiles <sub> --help`. Commands are grouped into
named Rich panels (Machine / Control / AI); the panel title carries the section
descriptor that the old hand-rolled help showed.
"""

import os
import sys
from pathlib import Path

import typer

from dotfiles.app.context import AppContext, build_real_context
from dotfiles.cmd.agent.cli import agent_app
from dotfiles.cmd.benchmark.cli import benchmark_app
from dotfiles.cmd.brew.cli import brew_app
from dotfiles.cmd.doctor.cli import doctor_command
from dotfiles.cmd.remote.cli import remote_app
from dotfiles.cmd.session.cli import session_app
from dotfiles.cmd.snapshot.cli import snapshot_app
from dotfiles.logging import configure_logging

# Rich help-panel titles. The em-dash descriptor is part of the panel title, so
# the grouped boxes read the same as the legacy `sub_help` section headers.
PANEL_MACHINE = "Machine — setup, maintenance, and machine-state"
PANEL_CONTROL = "Control — drive this Mac locally or from your phone"
PANEL_AI = "AI — agentic tooling and local models"

# Repo root (cli/src/dotfiles/app/main.py -> parents[4]), so the thin wrappers
# below can hand back to the bash shim for commands not yet ported to Python.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_SHIM = _REPO_ROOT / "bin" / "dotfiles"

# Let the bash-delegating wrappers forward any flags/args untouched.
_PASSTHROUGH = {"allow_extra_args": True, "ignore_unknown_options": True}

app = typer.Typer(
    name="dotfiles",
    help="Curated Mac dev environment: machine setup, remote control, and agentic tooling.",
    no_args_is_help=True,
    add_completion=False,
)


def _launch_tui() -> None:
    """Import lazily so non-TUI commands don't pay the Textual import cost."""
    from dotfiles.tui.app import MissionControlApp

    tui_app = MissionControlApp()
    tui_app.run()
    # The app exits (restoring the terminal) before handing off to zellij, so the
    # attached session gets a clean tty and actually receives keystrokes.
    if tui_app.handoff_command:
        os.execvp(tui_app.handoff_command[0], list(tui_app.handoff_command))


def _delegate_to_shim(name: str, args: list[str]) -> None:
    """Hand off to the bash shim's native implementation of *name*.

    These commands still live in bash; registering thin wrappers here keeps the
    top-level help unified and makes `dotfiles <name>` work even when invoked
    outside the shim (the shim itself routes them to bash before reaching Typer).
    """
    os.execvp(str(_SHIM), [str(_SHIM), name, *args])


@app.callback()
def _main(ctx: typer.Context) -> None:  # type: ignore[reportUnusedFunction]
    """Build the composition context once if a test hasn't injected one."""
    if ctx.obj is None:
        ctx.obj = build_real_context(interactive=sys.stdin.isatty())
    if isinstance(ctx.obj, AppContext):
        configure_logging(ctx.obj.settings.log_level)


# --- Machine -----------------------------------------------------------------
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


@app.command(rich_help_panel=PANEL_MACHINE, context_settings=_PASSTHROUGH)
def clean(ctx: typer.Context) -> None:
    """Clean up Homebrew caches."""
    _delegate_to_shim("clean", ctx.args)


@app.command(rich_help_panel=PANEL_MACHINE, context_settings=_PASSTHROUGH)
def dock(ctx: typer.Context) -> None:
    """Reset the macOS Dock layout."""
    _delegate_to_shim("dock", ctx.args)


app.add_typer(snapshot_app, name="snapshot", rich_help_panel=PANEL_MACHINE)


@app.command("profile-shell", rich_help_panel=PANEL_MACHINE, context_settings=_PASSTHROUGH)
def profile_shell(ctx: typer.Context) -> None:
    """Profile shell startup time."""
    _delegate_to_shim("profile-shell", ctx.args)


# --- Control -----------------------------------------------------------------
@app.command(rich_help_panel=PANEL_CONTROL)
def tui() -> None:
    """Launch the Mission Control TUI (phone-drivable dashboard)."""
    _launch_tui()


app.add_typer(remote_app, name="remote", rich_help_panel=PANEL_CONTROL)
app.add_typer(session_app, name="session", rich_help_panel=PANEL_CONTROL)

# --- AI ----------------------------------------------------------------------
app.add_typer(agent_app, name="agent", rich_help_panel=PANEL_AI)
app.add_typer(benchmark_app, name="benchmark", rich_help_panel=PANEL_AI)


def print_help() -> None:
    """Print the brand banner, then the unified Rich help. Called by the bash shim.

    Rendering the real Typer help here (rather than a parallel hand-rolled screen)
    guarantees the top-level help matches every `dotfiles <sub> --help` exactly.
    """
    import contextlib

    from dotfiles.banner import print_banner

    print_banner()
    # Drive Typer's own renderer so this screen matches every `dotfiles <sub>
    # --help`. prog_name drives the "Usage:" line; the shim is reached as `dfs`.
    # Typer raises SystemExit after printing --help; swallow it so the shim's
    # caller sees a normal return.
    with contextlib.suppress(SystemExit):
        app(args=["--help"], prog_name="dfs", standalone_mode=True)


if __name__ == "__main__":  # pragma: no cover
    app()
