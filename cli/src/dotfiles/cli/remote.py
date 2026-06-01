"""`dotfiles remote` commands: set up / disable the phone remote-shell entrypoint."""

import typer

from dotfiles.cli.context import AppContext
from dotfiles.cli.ui import has_errors, render_connection_info, render_steps
from dotfiles.console import console
from dotfiles.core.remote import InvalidKeyError, RemoteService

remote_app = typer.Typer(help="Set up or disable phone (Termius) remote-shell access.")


def _service(ctx: typer.Context) -> RemoteService:
    app_ctx = ctx.obj
    assert isinstance(app_ctx, AppContext)
    return RemoteService(
        runner=app_ctx.runner,
        interactive=app_ctx.interactive,
        home=app_ctx.home,
    )


@remote_app.command()
def setup(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print actions without changing anything."
    ),
    add_key: str | None = typer.Option(None, "--add-key", help="Termius public key to authorize."),
    harden_ssh: bool = typer.Option(False, "--harden-ssh", help="Disable SSH password auth."),
    session: str | None = typer.Option(None, "--session", help="Zellij session name."),
) -> None:
    """Set up SSH/Mosh/Zellij access for Termius."""
    app_ctx = ctx.obj
    assert isinstance(app_ctx, AppContext)
    service = _service(ctx)
    chosen = session or app_ctx.settings.default_session
    try:
        steps = service.setup(dry_run=dry_run, add_key=add_key, harden=harden_ssh, session=chosen)
    except InvalidKeyError:
        console.print("[red]--add-key does not look like an SSH public key[/]")
        raise typer.Exit(code=1) from None
    render_steps(console, steps)
    render_connection_info(console, service.connection_info(chosen))
    if has_errors(steps):
        raise typer.Exit(code=1)


@remote_app.command()
def disable(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print actions without changing anything."
    ),
    kill_sessions: bool = typer.Option(
        False, "--kill-sessions", help="Also kill existing mosh-server/sshd sessions."
    ),
) -> None:
    """Turn off macOS Remote Login (and optionally kill live sessions)."""
    steps = _service(ctx).disable(dry_run=dry_run, kill_sessions=kill_sessions)
    render_steps(console, steps)
    if has_errors(steps):
        raise typer.Exit(code=1)
