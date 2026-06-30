"""Top-level Typer application. Subcommands are mounted here; logic lives in core.

The whole command tree — including the handful of commands still implemented in
the bash shim — is registered here. Commands are grouped into named Rich panels
(Machine / Control / AI); the panel title carries the section descriptor that the
old hand-rolled help showed. Per-command help (`dotfiles <sub> --help`) uses
Typer's native renderer; the branded top-level help (`render_help_tree`) draws a
custom tree so each group's subcommands are visible on the front door.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import typer

from dotfiles.app.fuzzy import FuzzyTyperGroup

if TYPE_CHECKING:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from typer.core import TyperGroup

from dotfiles.app.context import AppContext, build_real_context
from dotfiles.cmd.agent.cli import agent_app
from dotfiles.cmd.benchmark.cli import benchmark_app
from dotfiles.cmd.brew.cli import brew_app
from dotfiles.cmd.doctor.cli import doctor_command
from dotfiles.cmd.email.cli import email_app
from dotfiles.cmd.remote.cli import remote_app
from dotfiles.cmd.repo.cli import repo_app
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
    cls=FuzzyTyperGroup,
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
app.add_typer(repo_app, name="repo", rich_help_panel=PANEL_MACHINE)


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
app.add_typer(email_app, name="email", rich_help_panel=PANEL_CONTROL)

# --- AI ----------------------------------------------------------------------
app.add_typer(agent_app, name="agent", rich_help_panel=PANEL_AI)
app.add_typer(benchmark_app, name="benchmark", rich_help_panel=PANEL_AI)


def _subcommand_rows(group: TyperGroup) -> list[tuple[Text, Text]]:
    """Build the dimmed ├/└ branch rows for a group's subcommands, in order."""
    from rich.text import Text

    items = list(group.commands.items())
    last = len(items) - 1
    return [
        (
            Text(f"  {'└' if i == last else '├'} {name}", style="dim"),
            Text(cmd.get_short_help_str(120), style="dim"),
        )
        for i, (name, cmd) in enumerate(items)
    ]


def _command_panel(root: TyperGroup, panel_title: str) -> Panel:
    """Build one Machine/Control/AI panel: every leaf command and group assigned to
    it (registration order), each group trailed by its subcommands as a branch."""
    from rich import box
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from typer.core import TyperGroup

    table = Table.grid(padding=(0, 2))
    table.add_column(no_wrap=True)
    table.add_column(overflow="fold")
    for name, cmd in root.commands.items():
        if getattr(cmd, "rich_help_panel", None) != panel_title:
            continue
        table.add_row(Text(name, style="bold cyan"), Text(cmd.get_short_help_str(120)))
        if isinstance(cmd, TyperGroup):
            for left, right in _subcommand_rows(cmd):
                table.add_row(left, right)
    return Panel(table, title=panel_title, title_align="left", box=box.ROUNDED, padding=(0, 1))


def render_help_tree(console: Console) -> None:
    """Render the branded top-level help with every sub-app's subcommands nested in.

    Typer's flat renderer hides each group's capabilities behind a single row
    (`agent` alone buries nine subcommands). This draws the *full* command tree —
    each group followed by its subcommands as an indented, dimmed branch — so the
    front door advertises what the CLI can actually do.

    Driven entirely by Click introspection of `app`, so the catalog stays
    single-sourced; there is no parallel list to drift. `dfs <sub> --help` is left
    on Typer's native renderer, so per-command help is unaffected.
    """
    import typer.main
    from rich import box
    from rich.padding import Padding
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from typer.core import TyperGroup

    root = typer.main.get_command(app)
    assert isinstance(root, TyperGroup)  # the top-level app is always a group

    # Usage + description, kept faithful to Typer's own top-of-help layout.
    console.print()
    console.print(Text.assemble((" Usage: ", "bold"), "dfs [OPTIONS] COMMAND [ARGS]..."))
    if app.info.help:
        console.print()
        console.print(Padding(Text(app.info.help), (0, 0, 0, 1)))
    console.print()

    options = Table.grid(padding=(0, 2))
    options.add_column(no_wrap=True, style="cyan")
    options.add_column()
    options.add_row("--help", "Show this message and exit.")
    console.print(
        Panel(options, title="Options", title_align="left", box=box.ROUNDED, padding=(0, 1))
    )

    # One panel per Machine/Control/AI group, subcommands nested beneath each group.
    for panel_title in (PANEL_MACHINE, PANEL_CONTROL, PANEL_AI):
        console.print(_command_panel(root, panel_title))


def print_help() -> None:
    """Print the brand banner, then the unified Rich help. Called by the bash shim."""
    from rich.console import Console

    from dotfiles.banner import print_banner

    print_banner()
    render_help_tree(Console())


if __name__ == "__main__":  # pragma: no cover
    app()
