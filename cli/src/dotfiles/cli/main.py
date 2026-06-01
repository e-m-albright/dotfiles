"""Top-level Typer application. Subcommands are mounted here; logic lives in core."""

import sys

import typer

from dotfiles import __version__
from dotfiles.cli.agent import agent_app
from dotfiles.cli.brew import brew_app
from dotfiles.cli.context import build_real_context
from dotfiles.cli.doctor import doctor_command
from dotfiles.cli.fleet import fleet_app
from dotfiles.cli.ledger import ledger_app
from dotfiles.cli.llm import llm_app
from dotfiles.cli.remote import remote_app
from dotfiles.cli.scaffold import scaffold_command
from dotfiles.cli.session import session_app
from dotfiles.cli.snapshot import snapshot_app
from dotfiles.console import console

app = typer.Typer(
    name="dotfiles",
    help="Hexagonal CLI for the dotfiles dev environment.",
    no_args_is_help=True,
    add_completion=False,
)


def _launch_tui() -> None:
    """Import lazily so non-TUI commands don't pay the Textual import cost."""
    from dotfiles.tui.app import MissionControlApp

    MissionControlApp().run()


@app.callback()
def _main(ctx: typer.Context) -> None:  # type: ignore[reportUnusedFunction]
    """Build the composition context once if a test hasn't injected one."""
    if ctx.obj is None:
        ctx.obj = build_real_context(interactive=sys.stdin.isatty())


# Command tree.
app.add_typer(remote_app, name="remote")
app.add_typer(session_app, name="session")
app.add_typer(session_app, name="sesh")
app.command("doctor")(doctor_command)
app.add_typer(brew_app, name="brew")
app.add_typer(agent_app, name="agent")
app.command("scaffold")(scaffold_command)
app.add_typer(llm_app, name="llm")
app.add_typer(snapshot_app, name="snapshot")
app.add_typer(ledger_app, name="ledger")
app.add_typer(fleet_app, name="fleet")


@app.command()
def tui() -> None:
    """Launch the Mission Control TUI."""
    _launch_tui()


@app.command()
def version() -> None:
    """Print the dotfiles-cli version."""
    console.print(__version__)


if __name__ == "__main__":  # pragma: no cover
    app()
