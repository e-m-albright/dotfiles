"""`dotfiles remote` - phone access entrypoints (Tailscale, Paseo, Zellij web)."""

import typer
from rich.console import Console

from dotfiles.app.context import app_context
from dotfiles.app.fuzzy import FuzzyTyperGroup
from dotfiles.cmd.remote.models import ZELLIJ_WEB_PORT, ConnectionInfo, RemoteStatus
from dotfiles.cmd.remote.service import RemoteService
from dotfiles.console import (
    console,
    has_errors,
    print_child,
    print_field,
    print_status,
    print_title,
    render_steps,
)
from dotfiles.result import StepResult

remote_app = typer.Typer(
    cls=FuzzyTyperGroup, help="Configure phone access or enter a project agent session."
)
zellij_app = typer.Typer(
    cls=FuzzyTyperGroup,
    help="Manage the Zellij web client and its tailnet exposure.",
)
remote_app.add_typer(zellij_app, name="zellij")


def _service(ctx: typer.Context) -> RemoteService:
    app_ctx = app_context(ctx)
    return RemoteService(runner=app_ctx.runner, home=app_ctx.home)


def _tailscale_value(status: RemoteStatus) -> str:
    if status.tailscale_connected:
        return f"connected · {status.tailnet_ip}"
    return "not connected"


def render_connection_info(console: Console, info: ConnectionInfo) -> None:
    """Print how to reach the phone surfaces (over Tailscale)."""
    print_title(console, "Phone access", "phone")
    if not info.tailnet_ip:
        print_status(
            console,
            "warn",
            "Tailscale not connected — start it before reaching the Mac off home Wi-Fi",
        )
    # Primary daily surface: the Paseo app (direct tailnet connection, no relay).
    print_field(console, "Paseo", info.paseo_addr, soft_wrap=True)
    console.print("  [dim]In the Paseo app, add this daemon address + your daemon password.[/]")
    console.print()
    # Fallback: the Zellij web client (browser terminal), deep-linked to the session.
    print_field(console, "Zellij web", info.phone_url, soft_wrap=True)
    print_field(console, "On this Mac", info.local_url, soft_wrap=True)
    console.print("  [dim]Zellij login token from[/] dfs remote zellij --new-token")


@remote_app.command()
def on(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print actions without changing anything."
    ),
    session: str | None = typer.Option(None, "--session", help="Zellij session name."),
    no_tailscale: bool = typer.Option(False, "--no-tailscale", help="Skip bringing Tailscale up."),
) -> None:
    """Bring phone access up and print the connection info.

    Brings Tailscale up (unless --no-tailscale), ensures the Paseo daemon and the
    Zellij web client (both launchd agents) are running, exposes the Zellij client
    over the tailnet with `tailscale serve`, and checks the `mobile` session.
    Manage individual services with `dfs remote paseo|tailscale|zellij`.
    """
    app_ctx = app_context(ctx)
    service = _service(ctx)
    chosen = session or app_ctx.settings.default_session
    print_title(console, "Remote", "on")
    steps: list[StepResult] = []
    if not no_tailscale:
        steps.append(service.tailscale_up(dry_run=dry_run))
    steps.extend(service.ensure_paseo_agent(dry_run=dry_run))
    steps.extend(service.ensure_zellij_agent(dry_run=dry_run))
    steps.append(service.serve_start(dry_run=dry_run))
    steps.append(service.mobile_session_step(chosen, dry_run=dry_run))
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
) -> None:
    """Cut off remote access without stopping local agents.

    Removes the Zellij tailnet route and brings Tailscale down, making both
    Paseo and Zellij unreachable remotely. Their local processes keep running.
    """
    service = _service(ctx)
    print_title(console, "Remote", "off")
    steps = [
        service.serve_reset(dry_run=dry_run),
        service.tailscale_down(dry_run=dry_run),
    ]
    render_steps(console, steps)
    console.print(
        "\n  [dim]Paseo, Zellij, and active agents keep running locally; "
        "Tailscale connectivity is off.[/]"
    )
    if has_errors(steps):
        raise typer.Exit(code=1)


def _paseo_action_steps(
    service: RemoteService,
    *,
    start: bool,
    stop: bool,
    rotate_password: bool,
    dry_run: bool,
) -> list[StepResult]:
    if stop:
        return service.paseo_uninstall_agent(dry_run=dry_run)
    if start:
        return service.paseo_install_agent(dry_run=dry_run)
    assert rotate_password
    return service.paseo_rotate_password(dry_run=dry_run)


def _render_paseo_action_result(
    steps: list[StepResult],
    *,
    info: ConnectionInfo,
    show_address: bool,
    rotate_password: bool,
    dry_run: bool,
) -> None:
    render_steps(console, steps)
    succeeded = not has_errors(steps)
    if show_address and not dry_run and succeeded:
        print_field(console, "Address", info.paseo_addr, soft_wrap=True)
    if rotate_password and not dry_run and succeeded:
        console.print("  [dim]Update the saved password in desktop and mobile clients.[/]")
        console.print("  [dim]Store the new password in your password manager.[/]")


@remote_app.command()
def paseo(
    ctx: typer.Context,
    start: bool = typer.Option(False, "--start", help="Install + load the Paseo daemon agent."),
    stop: bool = typer.Option(False, "--stop", help="Unload the Paseo daemon agent."),
    rotate_password: bool = typer.Option(
        False,
        "--rotate-password",
        help="Securely prompt for a new password and reload the daemon.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print actions without changing anything."
    ),
) -> None:
    """Turn the Paseo daemon on/off, or show its state.

    The Paseo app connects DIRECTLY over the tailnet (no relay, no `serve`), so
    this only manages the launchd agent. Tailscale-only is a deliberate
    boundary — do not add relay/QR pairing back (see the warning in
    service.py). With no flag, reports state and address. Password rotation
    uses Paseo's own hidden prompt; the password never passes through or
    appears in dotfiles CLI output.
    """
    if sum((start, stop, rotate_password)) > 1:
        raise typer.BadParameter("Choose only one of --start, --stop, or --rotate-password")

    app_ctx = app_context(ctx)
    service = _service(ctx)
    info = service.connection_info(app_ctx.settings.default_session)
    print_title(console, "Remote", "paseo")
    if not any((start, stop, rotate_password)):
        print_field(console, "Paseo", "running" if service.paseo_running() else "stopped")
        print_field(console, "Address", info.paseo_addr, soft_wrap=True)
        return
    if rotate_password:
        print_status(console, "warn", "Restarting the daemon may interrupt active Paseo runs")
    steps = _paseo_action_steps(
        service,
        start=start,
        stop=stop,
        rotate_password=rotate_password,
        dry_run=dry_run,
    )
    _render_paseo_action_result(
        steps,
        info=info,
        show_address=start or rotate_password,
        rotate_password=rotate_password,
        dry_run=dry_run,
    )
    if has_errors(steps):
        raise typer.Exit(code=1)


def _zellij_action_steps(
    service: RemoteService,
    *,
    start: bool,
    stop: bool,
    new_token: bool,
    dry_run: bool,
) -> list[StepResult]:
    if start:
        return [
            *service.ensure_zellij_agent(dry_run=dry_run),
            service.serve_start(dry_run=dry_run),
        ]
    if stop:
        return [
            service.serve_reset(dry_run=dry_run),
            *service.zellij_uninstall_agent(dry_run=dry_run),
        ]
    if new_token:
        if dry_run:
            return [StepResult(level="info", message="DRY RUN: mint a Zellij web token")]
        return [service.web_token()]
    return [service.web_status()]


@zellij_app.callback(invoke_without_command=True)
def zellij(
    ctx: typer.Context,
    start: bool = typer.Option(False, "--start", help="Start Zellij web and expose it."),
    stop: bool = typer.Option(False, "--stop", help="Remove exposure and stop Zellij web."),
    new_token: bool = typer.Option(False, "--new-token", help="Mint a one-time login token."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print lifecycle actions without changing anything."
    ),
) -> None:
    """Manage the launchd-owned Zellij web client and its tailnet route."""
    if ctx.invoked_subcommand is not None:
        return
    if sum((start, stop, new_token)) > 1:
        raise typer.BadParameter("Choose only one of --start, --stop, or --new-token")

    steps = _zellij_action_steps(
        _service(ctx),
        start=start,
        stop=stop,
        new_token=new_token,
        dry_run=dry_run,
    )
    render_steps(console, steps)
    if not has_errors(steps) and not (stop or new_token):
        console.print(f"\n[dim]Local:[/] http://127.0.0.1:{ZELLIJ_WEB_PORT}/mobile")
    if has_errors(steps):
        raise typer.Exit(code=1)


@zellij_app.command()
def qr(ctx: typer.Context) -> None:
    """Print a scannable QR of the Zellij web phone URL."""
    import segno

    app_ctx = app_context(ctx)
    service = _service(ctx)
    info = service.connection_info(app_ctx.settings.default_session)
    print_title(console, "Zellij web", "qr")
    if not info.magic_dns:
        print_status(
            console, "warn", "Tailscale not connected — the phone URL needs the tailnet up"
        )
        raise typer.Exit(code=1)
    segno.make(info.phone_url).terminal(compact=True)
    print_field(console, "URL", info.phone_url, soft_wrap=True)


@remote_app.command()
def tailscale(
    ctx: typer.Context,
    up: bool = typer.Option(False, "--up", help="Connect this machine to its tailnet."),
    down: bool = typer.Option(False, "--down", help="Disconnect this machine from its tailnet."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print actions without changing anything."
    ),
) -> None:
    """Manage this machine's Tailscale connectivity."""
    if up and down:
        raise typer.BadParameter("Choose only one of --up or --down")
    service = _service(ctx)
    if up:
        step = service.tailscale_up(dry_run=dry_run)
    elif down:
        step = service.tailscale_down(dry_run=dry_run)
    else:
        connected, ip = service.tailscale_status()
        print_field(console, "Tailscale", f"connected · {ip}" if connected else "not connected")
        return
    render_steps(console, [step])
    if step.level == "error":
        raise typer.Exit(code=1)


@remote_app.command()
def status(ctx: typer.Context) -> None:
    """Show phone-access state: Tailscale, Paseo, the Zellij web fallback, and addresses."""
    app_ctx = app_context(ctx)
    service = _service(ctx)
    s = service.status()
    print_title(console, "Remote", "status")
    print_field(console, "Tailscale", _tailscale_value(s))
    print_field(console, "Paseo", "running" if s.paseo_running else "stopped")
    print_field(console, "Zellij web", "running" if s.zellij_web_running else "stopped")
    print_field(console, "Host", f"{s.user}@{s.host}")
    if s.magic_dns:
        info = service.connection_info(app_ctx.settings.default_session)
        print_child(console, "Paseo addr", info.paseo_addr)
        print_child(console, "Zellij URL", info.phone_url, last=True, soft_wrap=True)
