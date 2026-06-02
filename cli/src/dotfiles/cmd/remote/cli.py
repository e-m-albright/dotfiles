"""`dotfiles remote on|off|status` — the phone (Termius) remote-shell entrypoint."""

import typer
from rich.console import Console

from dotfiles.app.context import app_context
from dotfiles.cmd.remote.models import ConnectionInfo
from dotfiles.cmd.remote.service import InvalidKeyError, RemoteService
from dotfiles.console import console, has_errors, render_and_exit, render_steps

remote_app = typer.Typer(help="Turn phone (Termius) remote-shell access on or off.")


def _service(ctx: typer.Context) -> RemoteService:
    app_ctx = app_context(ctx)
    return RemoteService(
        runner=app_ctx.runner,
        interactive=app_ctx.interactive,
        home=app_ctx.home,
    )


def render_connection_info(console: Console, info: ConnectionInfo) -> None:
    """Print the Termius/Mosh connection details for a connection info."""
    console.print("\n[bold]Termius setup[/]")
    console.print(f"  Host: {info.host}")
    if info.tailnet_ip:
        console.print(f"  Tailscale IP: {info.tailnet_ip}")
    else:
        console.print(
            "  [yellow]⚠[/] Tailscale does not look connected. "
            "Start Tailscale before connecting from your phone"
        )
    console.print(f"  Username: {info.user}")
    console.print("  Protocol: Mosh")
    console.print("\n[bold]Paste into Termius as the Mosh command:[/]")
    console.print(info.mosh_command, soft_wrap=True)
    console.print("\n[dim]Or connect and pick a live session:[/]")
    picker_cmd = info.mosh_command.replace(info.startup_command, "dotfiles sesh")
    console.print(picker_cmd, soft_wrap=True)


@remote_app.command()
def on(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print actions without changing anything."
    ),
    add_key: str | None = typer.Option(None, "--add-key", help="Termius public key to authorize."),
    harden_ssh: bool = typer.Option(False, "--harden-ssh", help="Disable SSH password auth."),
    session: str | None = typer.Option(None, "--session", help="Zellij session name."),
) -> None:
    """Turn on SSH/Mosh/Zellij access for Termius."""
    app_ctx = app_context(ctx)
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
def off(
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
    render_and_exit(console, steps)


@remote_app.command()
def status(ctx: typer.Context) -> None:
    """Show the Mac's remote-shell entrypoint state."""
    s = _service(ctx).status()
    login = "[green]on[/]" if s.remote_login_on else "[dim]off[/]"
    tail = s.tailnet_ip or "—"
    tail_state = "connected" if s.tailscale_connected else "down"
    console.print(f"Remote Login: {login}")
    console.print(f"Tailscale: {tail_state} ({tail})")
    console.print(f"{s.user}@{s.host}")
