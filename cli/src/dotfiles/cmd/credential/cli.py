"""`dotfiles credential` inventory, enrollment, and Pi linkage commands."""

from __future__ import annotations

import json
import os
from typing import Annotated, NoReturn

import typer
from rich.table import Table

from dotfiles.app.context import app_context
from dotfiles.cmd.credential.models import CredentialRecord
from dotfiles.cmd.credential.service import (
    CredentialInventoryError,
    CredentialService,
    initialize_inventory,
)
from dotfiles.console import console, print_status, print_title

credential_app = typer.Typer(
    help="Inventory local programmatic credentials without exposing values."
)
_SECRET_SUFFIXES = ("_API_KEY", "_AUTH_TOKEN", "_OAUTH_TOKEN")
_SECRET_NAMES = {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"}


def _service(ctx: typer.Context) -> CredentialService:
    app_ctx = app_context(ctx)
    return CredentialService(runner=app_ctx.runner, home=app_ctx.home)


def _fail(exc: CredentialInventoryError) -> NoReturn:
    print_status(console, "error", str(exc))
    raise typer.Exit(1) from exc


@credential_app.command("init")
def initialize(ctx: typer.Context) -> None:
    """Create a private metadata-only starter inventory."""
    try:
        path = initialize_inventory(app_context(ctx).home)
    except CredentialInventoryError as exc:
        _fail(exc)
    print_status(console, "success", f"Created {path}")


def _json_record(record: CredentialRecord) -> dict[str, object]:
    spec = record.spec
    return {
        "id": spec.id,
        "label": spec.label,
        "provider": spec.provider,
        "kind": spec.kind,
        "backend": spec.backend,
        "service": spec.service,
        "path": spec.path,
        "environment": spec.environment,
        "pi_provider": spec.pi_provider,
        "status": record.status,
        "consumers": list(spec.consumers),
        "scopes": list(spec.scopes),
        "expires_on": spec.expires_on.isoformat() if spec.expires_on else None,
        "rotation": spec.rotation,
        "disposition": spec.disposition,
        "required": spec.required,
        "restore": spec.restore,
        "note": spec.note,
        "detail": record.detail,
    }


def _render_records(records: list[CredentialRecord]) -> None:
    print_title(console, "credential", "list")
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("Grant", no_wrap=True, overflow="ellipsis", max_width=22)
    table.add_column("Status", no_wrap=True)
    table.add_column("Consumer boundary", ratio=1)
    table.add_column("Access and expiry", ratio=1)
    status_styles = {
        "stored": "green",
        "missing": "yellow",
        "expired": "red",
        "inaccessible": "red",
        "superseded": "dim",
        "deferred": "dim",
    }
    for record in records:
        spec = record.spec
        expiry = (
            f"expires {spec.expires_on.isoformat()}"
            if spec.expires_on
            else f"rotation: {spec.rotation}"
        )
        access = ", ".join(spec.scopes) or "unannotated"
        table.add_row(
            spec.id,
            f"[{status_styles[record.status]}]{record.status}[/]",
            ", ".join(spec.consumers) or "-",
            f"{access}; {expiry}",
        )
    console.print(table)
    console.print()


@credential_app.command("list")
def list_credentials(
    ctx: typer.Context,
    as_json: Annotated[
        bool, typer.Option("--json", help="Emit stable machine-readable JSON.")
    ] = False,
) -> None:
    """Show every grant, its consumer boundary, and bounded local status."""
    try:
        records = _service(ctx).list()
    except CredentialInventoryError as exc:
        _fail(exc)
    if as_json:
        typer.echo(json.dumps([_json_record(record) for record in records], indent=2))
        return
    _render_records(records)


@credential_app.command("run", context_settings={"allow_extra_args": True})
def run_with_credential(
    ctx: typer.Context,
    credential_id: str,
    command: Annotated[list[str], typer.Argument(help="Command and arguments after --.")],
) -> None:
    """Resolve one grant into its declared environment variable and exec a command."""
    if not command:
        print_status(console, "error", "a command is required after --")
        raise typer.Exit(2)
    try:
        name, value = _service(ctx).resolve_environment(credential_id)
    except CredentialInventoryError as exc:
        _fail(exc)
    environment = {
        key: existing
        for key, existing in os.environ.items()
        if not key.endswith(_SECRET_SUFFIXES) and key not in _SECRET_NAMES
    }
    environment[name] = value
    os.execvpe(command[0], command, environment)


@credential_app.command("set")
def set_credential(ctx: typer.Context, credential_id: str) -> None:
    """Prompt in the terminal and store one configured grant in macOS Keychain."""
    try:
        _service(ctx).set(credential_id)
    except CredentialInventoryError as exc:
        _fail(exc)
    print_status(console, "success", f"{credential_id} stored in Keychain")


@credential_app.command("link-pi")
def link_pi(
    ctx: typer.Context,
    credential_id: str,
    force: Annotated[
        bool, typer.Option("--force", help="Replace an existing Pi provider credential.")
    ] = False,
) -> None:
    """Configure Pi to resolve one API key from its Keychain grant."""
    try:
        path = _service(ctx).link_pi(credential_id, force=force)
    except CredentialInventoryError as exc:
        _fail(exc)
    print_status(console, "success", f"Pi now resolves {credential_id} from Keychain ({path})")
