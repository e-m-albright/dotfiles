"""`dotfiles remote on|off|status` — the phone (Termius) remote-shell entrypoint."""

import typer
from rich.console import Console

from dotfiles.app.context import app_context
from dotfiles.cmd.remote.models import ConnectionInfo, RemoteStatus
from dotfiles.cmd.remote.service import (
    SHARING_OPEN,
    SHARING_PATH,
    InvalidKeyError,
    RemoteService,
)
from dotfiles.console import (
    console,
    has_errors,
    print_child,
    print_field,
    print_status,
    print_title,
    render_steps,
)

remote_app = typer.Typer(help="Turn phone (Termius) remote-shell access on or off.")

_WAIT_TIMEOUT_MIN = 2


def _service(ctx: typer.Context) -> RemoteService:
    app_ctx = app_context(ctx)
    return RemoteService(
        runner=app_ctx.runner,
        interactive=app_ctx.interactive,
        home=app_ctx.home,
    )


def _tailscale_value(status: RemoteStatus) -> str:
    if status.tailscale_connected:
        return f"connected · {status.tailnet_ip}"
    return "not connected"


def _ssh_auth_value(status: RemoteStatus) -> str:
    if status.ssh_password_auth is True:
        return "password allowed (run `dfs remote on --harden-ssh`)"
    if status.ssh_password_auth is False:
        return "key-only"
    return "unknown"


def _wait_for_login(service: RemoteService, *, target: bool, interactive: bool) -> None:
    """Hold open with a spinner until Remote Login flips to *target*, then confirm.

    Only runs when ``AppContext.interactive`` is True (stdin is a TTY in production).
    Under a pipe or in CLI tests with ``interactive=False``, there's no one to flip
    the toggle — skip the wait and leave Settings open for the user.
    """
    if not interactive:
        return
    word = "on" if target else "off"
    with console.status(f"Waiting for Remote Login to turn {word}…"):
        flipped = service.wait_until_remote_login(target, timeout=_WAIT_TIMEOUT_MIN * 60)
    if flipped:
        print_status(console, "success", f"Remote Login is {word}")
    else:
        print_status(
            console,
            "warn",
            f"Still {'off' if target else 'on'} after {_WAIT_TIMEOUT_MIN} min — left Settings open",
        )
        raise typer.Exit(code=1)


def render_connection_info(console: Console, info: ConnectionInfo) -> None:
    """Print the Termius/Mosh connection details in the shared field-column style."""
    print_title(console, "Termius", "phone")
    console.print("  [dim]Enter these in the Termius app (it's a GUI, not a command):[/]")
    if info.tailnet_ip:
        print_field(console, "Address", f"{info.tailnet_ip}   (or {info.host})")
    else:
        print_field(console, "Address", info.host)
        print_status(
            console,
            "warn",
            "Tailscale not connected — start it before connecting off your home Wi-Fi",
        )
    print_field(console, "Username", info.user)
    print_field(console, "Protocol", "Mosh")
    print_field(console, "Mosh srv", info.mosh_server)
    print_field(console, "Startup", info.startup_command)
    console.print()
    console.print("  [dim]Desktop-to-desktop mosh command (not pasted into Termius):[/]")
    console.print(info.mosh_command, soft_wrap=True)
    console.print("  [dim]Same, but into the live-session picker:[/]")
    picker_cmd = info.mosh_command.replace(info.startup_command, "dotfiles session")
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
    tailscale: bool = typer.Option(
        False, "--tailscale", help="Also bring Tailscale up (tailscale up)."
    ),
) -> None:
    """Turn on SSH/Mosh/Zellij access for Termius."""
    app_ctx = app_context(ctx)
    service = _service(ctx)
    chosen = session or app_ctx.settings.default_session
    print_title(console, "Remote", "on")
    pre_steps = [service.tailscale_up(dry_run=dry_run)] if tailscale else []
    try:
        steps = service.setup(dry_run=dry_run, add_key=add_key, harden=harden_ssh, session=chosen)
    except InvalidKeyError:
        console.print("[red]--add-key does not look like an SSH public key[/]")
        raise typer.Exit(code=1) from None
    render_steps(console, pre_steps + steps)
    if not dry_run and not service.remote_login_on():
        _wait_for_login(service, target=True, interactive=app_ctx.interactive)
    render_connection_info(console, service.connection_info(chosen))
    if has_errors(pre_steps + steps):
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
    tailscale: bool = typer.Option(
        False, "--tailscale", help="Also bring Tailscale down (tailscale down)."
    ),
) -> None:
    """Open the Remote Login toggle, hold until it flips off, then confirm.

    Remote Login is flipped by hand in System Settings — this CLI can't toggle it
    (needs Full Disk Access) — so it opens the exact pane and waits for the flip.
    `--kill-sessions` also drops open mosh/sshd logins.
    """
    app_ctx = app_context(ctx)
    service = _service(ctx)
    print_title(console, "Remote", "off")

    steps = [service.tailscale_down(dry_run=dry_run)] if tailscale else []
    on_now = service.remote_login_on()
    if on_now:
        if not dry_run:
            service.open_sharing_pane()
        print_status(console, "warn", "Remote Login is ON", sub="Turn it off to stop new logins.")
    else:
        print_status(console, "success", "Remote Login already disabled")
    steps.extend(service.disable_intro(dry_run=dry_run, kill_sessions=kill_sessions))
    render_steps(console, steps)

    console.print()
    if on_now:
        print_field(console, "Settings", SHARING_PATH)
        print_field(console, "Shortcut", SHARING_OPEN, soft_wrap=True)
    print_field(console, "Tailscale", _tailscale_value(service.status()))

    if on_now and not dry_run:
        _wait_for_login(service, target=False, interactive=app_ctx.interactive)
    if has_errors(steps):
        raise typer.Exit(code=1)


@remote_app.command()
def web(
    ctx: typer.Context,
    start: bool = typer.Option(False, "--start", help="Start the web server (daemonized)."),
    stop: bool = typer.Option(False, "--stop", help="Stop the web server."),
    new_token: bool = typer.Option(False, "--new-token", help="Mint a one-time login token."),
) -> None:
    """Experimental: serve zellij sessions to a browser (Termius/Mosh stays primary).

    With no flag, reports server status. Reachable from the phone only after you
    set web_server_ip + TLS certs in the zellij config (terminal/zellij/config.kdl).
    """
    service = _service(ctx)
    if start:
        step = service.web_start()
    elif stop:
        step = service.web_stop()
    elif new_token:
        step = service.web_token()
    else:
        step = service.web_status()
    render_steps(console, [step])
    if step.level != "error" and not (stop or new_token):
        console.print(
            "\n[dim]Local:[/] http://127.0.0.1:8082/mobile"
            "\n[dim]Phone access needs web_server_ip + TLS in[/] "
            "terminal/zellij/config.kdl[dim]; until then use Termius/Mosh.[/]"
        )
    if step.level == "error":
        raise typer.Exit(code=1)


@remote_app.command()
def status(ctx: typer.Context) -> None:
    """Show the Mac's remote-shell entrypoint state."""
    s = _service(ctx).status()
    print_title(console, "Remote", "status")
    # Remote Login is the category header; how-to-change-it (SSH auth when on,
    # the Settings pane, the open shortcut) nests beneath it as owned children.
    print_field(console, "Remote Login", "on" if s.remote_login_on else "off")
    if s.remote_login_on:
        print_child(console, "SSH auth", _ssh_auth_value(s))
    print_child(console, "Settings", SHARING_PATH)
    print_child(console, "Shortcut", SHARING_OPEN, last=True, soft_wrap=True)
    print_field(console, "Tailscale", _tailscale_value(s))
    print_field(console, "Host", f"{s.user}@{s.host}")
