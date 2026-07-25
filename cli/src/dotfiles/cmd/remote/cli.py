"""`dotfiles remote` - phone access entrypoints (Tailscale, Paseo, Zellij web)."""

import typer
from rich.console import Console

from dotfiles.app.context import app_context
from dotfiles.app.fuzzy import FuzzyTyperGroup
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
    cls=FuzzyTyperGroup, help="Configure phone access or enter a project agent session."
)


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
    console.print("  [dim]Zellij login token from[/] dfs remote web --new-token")


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
    Manage a single surface with `dfs remote paseo|web`.
    """
    app_ctx = app_context(ctx)
    service = _service(ctx)
    chosen = session or app_ctx.settings.default_session
    print_title(console, "Remote", "on")
    steps: list[StepResult] = []
    if not no_tailscale:
        steps.append(service.tailscale_up(dry_run=dry_run))
    steps.extend(service.paseo_install_agent(dry_run=dry_run))
    steps.extend(service.install_agent(dry_run=dry_run))
    steps.append(service.serve_start(dry_run=dry_run))
    steps.append(service.mobile_session_step(dry_run=dry_run))
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
    tailscale: bool = typer.Option(
        False, "--tailscale", help="Also bring Tailscale down (tailscale down)."
    ),
) -> None:
    """Stop exposing the Zellij web client over the tailnet.

    The servers keep running under launchd (Paseo stays reachable on the tailnet);
    this only tears down the `tailscale serve` route. `--tailscale` also brings the
    tailnet down, which cuts off Paseo too.
    """
    service = _service(ctx)
    print_title(console, "Remote", "off")
    steps = [service.serve_reset(dry_run=dry_run)]
    if tailscale:
        steps.append(service.tailscale_down(dry_run=dry_run))
    render_steps(console, steps)
    console.print(
        "\n  [dim]Servers keep running under launchd; this only stops the Zellij tailnet route.[/]"
    )
    if has_errors(steps):
        raise typer.Exit(code=1)


@remote_app.command()
def paseo(
    ctx: typer.Context,
    start: bool = typer.Option(False, "--start", help="Install + load the Paseo daemon agent."),
    stop: bool = typer.Option(False, "--stop", help="Unload the Paseo daemon agent."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print actions without changing anything."
    ),
) -> None:
    """Turn the Paseo daemon on/off, or show its state.

    The Paseo app connects DIRECTLY over the tailnet (no relay, no `serve`), so
    this only manages the launchd agent. With no flag, reports state and address.
    """
    app_ctx = app_context(ctx)
    service = _service(ctx)
    info = service.connection_info(app_ctx.settings.default_session)
    print_title(console, "Remote", "paseo")
    if stop:
        steps = service.paseo_uninstall_agent(dry_run=dry_run)
    elif start:
        steps = service.paseo_install_agent(dry_run=dry_run)
    else:
        print_field(console, "Paseo", "running" if service.paseo_running() else "stopped")
        print_field(console, "Address", info.paseo_addr, soft_wrap=True)
        return
    render_steps(console, steps)
    if start and not dry_run:
        print_field(console, "Address", info.paseo_addr, soft_wrap=True)
    if has_errors(steps):
        raise typer.Exit(code=1)


@remote_app.command()
def web(
    ctx: typer.Context,
    start: bool = typer.Option(False, "--start", help="Start the web server (daemonized)."),
    stop: bool = typer.Option(False, "--stop", help="Stop the web server."),
    new_token: bool = typer.Option(False, "--new-token", help="Mint a one-time login token."),
) -> None:
    """Serve zellij sessions to a browser; reach it from the phone over Tailscale.

    With no flag, reports server status. Keep the server on localhost and expose
    it to the tailnet with `tailscale serve --bg 8082` (TLS terminated for you).
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
            "\n[dim]Phone: expose over the tailnet with[/] tailscale serve --bg 8082"
            "[dim], then open[/] https://<your-tailnet-host>/mobile[dim] in a browser.[/]"
        )
    if step.level == "error":
        raise typer.Exit(code=1)


@remote_app.command()
def qr(ctx: typer.Context) -> None:
    """Print a scannable QR of the Zellij web phone URL (open it on the phone)."""
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
