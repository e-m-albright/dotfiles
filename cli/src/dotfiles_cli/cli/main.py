"""Top-level Typer application. Subcommands are mounted here; logic lives in core."""

import typer

from dotfiles_cli import __version__
from dotfiles_cli.console import console

app = typer.Typer(
    name="dotfiles",
    help="Hexagonal CLI for the dotfiles dev environment.",
    no_args_is_help=True,
    add_completion=False,
)


def _stub(name: str, display: str | None = None) -> typer.Typer:
    label = display or name
    sub = typer.Typer(help=f"{name} commands (implemented in a later phase).")

    @sub.callback(invoke_without_command=True)
    def _root() -> None:  # pragma: no cover  # type: ignore[reportUnusedFunction]
        console.print(f"[yellow]{label}[/] is not implemented yet.")

    return sub


# Command tree (stubs filled in by later phases P1b-P1d).
app.add_typer(_stub("remote"), name="remote")
app.add_typer(_stub("session"), name="session")
app.add_typer(_stub("session", display="sesh"), name="sesh")  # alias
app.add_typer(_stub("doctor"), name="doctor")
app.add_typer(_stub("brew"), name="brew")
app.add_typer(_stub("agent"), name="agent")
app.add_typer(_stub("verify"), name="verify")
app.add_typer(_stub("scaffold"), name="scaffold")
app.add_typer(_stub("llm"), name="llm")


@app.command()
def version() -> None:
    """Print the dotfiles-cli version."""
    console.print(__version__)


if __name__ == "__main__":  # pragma: no cover
    app()
