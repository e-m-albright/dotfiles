"""`dotfiles remote` — Tailscale-direct Paseo lifecycle and status."""

import typer
from rich.console import Console

from dotfiles.app.context import app_context
from dotfiles.cmd.remote.models import ConnectionInfo, RemoteStatus
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
    help="Manage Paseo phone access over the private Tailscale network.",
)


def _service(ctx: typer.Context) -> RemoteService:
    app_ctx = app_context(ctx)
    return RemoteService(runner=app_ctx.runner, home=app_ctx.home)


def _tailscale_value(status: RemoteStatus) -> str:
    if status.tailscale_connected:
        return f"connected · {status.tailnet_ip}"
    return "not connected"


def render_connection_info(console: Console, info: ConnectionInfo) -> None:
    print_title(console, "Phone access", "phone")
    if not info.tailnet_ip:
        print_status(
            console,
            "warn",
            "Tailscale not connected — start it before reaching the Mac off home Wi-Fi",
        )
    print_field(console, "Paseo", info.paseo_addr, soft_wrap=True)
    console.print("  [dim]Save this daemon address and its password in the Paseo app.[/]")


@remote_app.command()
def on(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print actions without changing anything."
    ),
    no_tailscale: bool = typer.Option(False, "--no-tailscale", help="Skip bringing Tailscale up."),
) -> None:
    """Bring Tailscale and the tailnet-bound Paseo daemon up."""
    service = _service(ctx)
    print_title(console, "Remote", "on")
    steps: list[StepResult] = []
    if not no_tailscale:
        steps.append(service.tailscale_up(dry_run=dry_run))
    steps.extend(service.ensure_paseo_agent(dry_run=dry_run))
    render_steps(console, steps)
    render_connection_info(console, service.connection_info())
    if has_errors(steps):
        raise typer.Exit(code=1)


@remote_app.command()
def off(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print actions without changing anything."
    ),
) -> None:
    """Cut off tailnet access without stopping local Paseo agents."""
    service = _service(ctx)
    print_title(console, "Remote", "off")
    steps = [service.tailscale_down(dry_run=dry_run)]
    render_steps(console, steps)
    console.print("\n  [dim]Paseo and active agents keep running locally.[/]")
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
    """Turn the direct-tailnet Paseo daemon on or off, or show its state."""
    if sum((start, stop, rotate_password)) > 1:
        raise typer.BadParameter("Choose only one of --start, --stop, or --rotate-password")

    service = _service(ctx)
    info = service.connection_info()
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
    """Show Tailscale, Paseo, and the direct daemon address."""
    service = _service(ctx)
    state = service.status()
    print_title(console, "Remote", "status")
    print_field(console, "Tailscale", _tailscale_value(state))
    print_field(console, "Paseo", "running" if state.paseo_running else "stopped")
    print_field(console, "Host", f"{state.user}@{state.host}")
    if state.tailnet_ip:
        print_child(console, "Paseo addr", service.connection_info().paseo_addr, last=True)
