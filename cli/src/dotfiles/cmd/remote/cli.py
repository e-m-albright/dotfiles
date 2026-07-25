"""`dotfiles remote` - phone access and project-agent entrypoints."""

import typer
from rich.console import Console

from dotfiles.app.context import app_context
from dotfiles.app.fuzzy import FuzzyTyperGroup
from dotfiles.cmd.remote.models import ConnectionInfo, RemoteStatus
from dotfiles.cmd.remote.pi import project_layout, resolve_project, session_name_for
from dotfiles.cmd.remote.service import RemoteService
from dotfiles.cmd.session.zellij import SessionError, Zellij
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
    """Print how to reach the phone web clients (over Tailscale)."""
    print_title(console, "Phone access", "phone")
    if not info.tailnet_ip:
        print_status(
            console,
            "warn",
            "Tailscale not connected — start it before reaching the Mac off home Wi-Fi",
        )
    # Primary daily surface: the ygncode Pi PWA.
    print_field(console, "Pi PWA", info.pi_web_url, soft_wrap=True)
    console.print("  [dim]token:[/] grep PI_WEB_TOKEN ~/.config/pi-web/env")
    console.print()
    # Fallback: the Zellij web client (browser terminal), deep-linked to the session.
    print_field(console, "Zellij web", info.phone_url, soft_wrap=True)
    print_field(console, "On this Mac", info.local_url, soft_wrap=True)
    console.print("  [dim]Expose over the tailnet with[/] tailscale serve --bg 8082")
    console.print("  [dim]Zellij login token from[/] dfs remote web --new-token")


@remote_app.command()
def on(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print actions without changing anything."
    ),
    session: str | None = typer.Option(None, "--session", help="Zellij session name."),
    tailscale: bool = typer.Option(
        False, "--tailscale", help="Also bring Tailscale up (tailscale up)."
    ),
) -> None:
    """Bring phone web-access up and print the connection info.

    Ensures the Zellij web client (launchd agent) and ygncode's pi-web service are
    running, then exposes the Zellij client over the tailnet with `tailscale serve`.
    """
    app_ctx = app_context(ctx)
    service = _service(ctx)
    chosen = session or app_ctx.settings.default_session
    print_title(console, "Remote", "on")
    steps: list[StepResult] = []
    if tailscale:
        steps.append(service.tailscale_up(dry_run=dry_run))
    steps.extend(service.install_agent(dry_run=dry_run))
    steps.append(service.pi_web_kick(dry_run=dry_run))
    steps.append(service.serve_start(dry_run=dry_run))
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
    """Stop exposing the phone web clients over the tailnet.

    The web servers keep running under launchd; this only tears down the
    `tailscale serve` routes. `--tailscale` also brings the tailnet down.
    """
    service = _service(ctx)
    print_title(console, "Remote", "off")
    steps = [service.serve_reset(dry_run=dry_run)]
    if tailscale:
        steps.append(service.tailscale_down(dry_run=dry_run))
    render_steps(console, steps)
    console.print(
        "\n  [dim]Web servers keep running under launchd; this only stops tailnet exposure.[/]"
    )
    if has_errors(steps):
        raise typer.Exit(code=1)


@remote_app.command()
def pi(ctx: typer.Context, project: str) -> None:
    """Attach to a project Zellij session and continue its latest pi conversation."""
    app_ctx = app_context(ctx)
    try:
        project_path = resolve_project(app_ctx.home, project)
        session_name = session_name_for(project_path)
    except ValueError as exc:
        print_status(console, "error", str(exc))
        raise typer.Exit(code=1) from exc

    zellij = Zellij(app_ctx.runner, home=app_ctx.home)
    try:
        exists = any(session.name == session_name for session in zellij.list_sessions())
    except SessionError as exc:
        print_status(console, "error", f"zellij error: {exc}")
        raise typer.Exit(code=1) from exc

    if exists:
        command = ("zellij", "attach", session_name)
    else:
        command = (
            "zellij",
            "--session",
            session_name,
            "--layout-string",
            project_layout(project_path, session_name),
        )
    app_ctx.launcher.attach(command)


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
def token(ctx: typer.Context) -> None:
    """Show ygncode pi-web's login token and a tap-ready phone URL."""
    app_ctx = app_context(ctx)
    service = _service(ctx)
    tok = service.pi_web_token()
    print_title(console, "Pi PWA", "token")
    if tok is None:
        print_status(
            console, "warn", "No pi-web token (~/.config/pi-web/env) — is ygncode installed?"
        )
        raise typer.Exit(code=1)
    info = service.connection_info(app_ctx.settings.default_session)
    print_field(console, "Token", tok)
    if info.magic_dns:
        print_field(console, "Phone URL", f"{info.pi_web_url}?token={tok}", soft_wrap=True)
    else:
        print_status(console, "warn", "Tailscale not connected — start it for the phone URL")


@remote_app.command()
def status(ctx: typer.Context) -> None:
    """Show phone-access state: Tailscale, the web servers, and the phone URLs."""
    app_ctx = app_context(ctx)
    service = _service(ctx)
    s = service.status()
    print_title(console, "Remote", "status")
    print_field(console, "Tailscale", _tailscale_value(s))
    print_field(console, "Zellij web", "running" if s.zellij_web_running else "stopped")
    pi_state = (
        "running" if s.pi_web_running else ("installed" if s.pi_web_installed else "not installed")
    )
    print_field(console, "Pi PWA (ygncode)", pi_state)
    print_field(console, "Host", f"{s.user}@{s.host}")
    if s.magic_dns:
        info = service.connection_info(app_ctx.settings.default_session)
        print_child(console, "Pi PWA URL", info.pi_web_url)
        print_child(console, "Zellij URL", info.phone_url, last=True, soft_wrap=True)
