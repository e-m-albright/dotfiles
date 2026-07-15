"""`dotfiles email-mask` commands: manage iCloud Hide My Email aliases."""

from __future__ import annotations

from typing import Annotated, NoReturn

import typer

from dotfiles.app.context import app_context
from dotfiles.app.fuzzy import FuzzyTyperGroup
from dotfiles.cmd.email.service import (
    MaskError,
    MaskProvider,
    copy_to_clipboard,
    create_mask,
    deactivate_mask,
    delete_mask,
    find_mask,
    list_masks,
)
from dotfiles.console import console, print_field, print_status, print_title

email_mask_app = typer.Typer(
    cls=FuzzyTyperGroup,
    help="Create and manage iCloud Hide My Email aliases.",
    invoke_without_command=True,
)

# Reused across every command; defaults to $DOTFILES_APPLE_ID via Settings.
_AppleId = Annotated[
    str | None,
    typer.Option("--apple-id", help="iCloud account (defaults to $DOTFILES_APPLE_ID)."),
]
_Selector = Annotated[str, typer.Argument(help="The alias address or its anonymous id.")]


def _provider(ctx: typer.Context, apple_id: str | None) -> MaskProvider:
    """Resolve the iCloud account and return a logged-in provider; exit 1 if unset."""
    app_ctx = app_context(ctx)
    account = apple_id or app_ctx.settings.apple_id
    if not account:
        print_status(
            console,
            "error",
            "No iCloud account set.",
            "Pass --apple-id you@icloud.com or set DOTFILES_APPLE_ID.",
        )
        raise typer.Exit(code=1)
    return app_ctx.mask_provider_factory(account)


def _fail(exc: MaskError) -> NoReturn:
    """Render an iCloud failure as a clean error line + exit 1 (no traceback)."""
    print_status(console, "error", str(exc))
    raise typer.Exit(code=1) from exc


def _create(ctx: typer.Context, label: str, apple_id: str | None, copy: bool) -> None:
    """Create and render one alias."""
    print_title(console, "email-mask", "create")
    provider = _provider(ctx, apple_id)
    try:
        reserved = create_mask(provider, label)
    except MaskError as exc:
        _fail(exc)
    print_status(console, "success", "New Hide My Email created")
    print_field(console, "address", reserved.address, soft_wrap=True)
    print_field(console, "label", reserved.label)
    if copy and copy_to_clipboard(app_context(ctx).runner, reserved.address):
        print_status(console, "info", "Copied to clipboard")
    console.print()


@email_mask_app.callback()
def email_mask(ctx: typer.Context) -> None:
    """Create a mask with the default label when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        _create(ctx, "dotfiles", None, True)


@email_mask_app.command()
def create(
    ctx: typer.Context,
    label: Annotated[
        str, typer.Argument(help="Label to file the alias under in iCloud settings.")
    ] = "dotfiles",
    apple_id: _AppleId = None,
    copy: Annotated[
        bool, typer.Option("--copy/--no-copy", help="Copy the new address to the clipboard.")
    ] = True,
) -> None:
    """Generate a fresh Hide My Email alias, reserve it, and copy it to the clipboard.

    First run prompts (once) for the iCloud password and a two-factor code, then
    persists the session — subsequent runs are non-interactive. Requires iCloud+.
    """
    _create(ctx, label, apple_id, copy)


@email_mask_app.command("list")
def list_aliases(ctx: typer.Context, apple_id: _AppleId = None) -> None:
    """List your aliases — address, label, and whether forwarding is active."""
    print_title(console, "email-mask", "list")
    provider = _provider(ctx, apple_id)
    try:
        masks = list_masks(provider)
    except MaskError as exc:
        _fail(exc)
    if not masks:
        print_status(console, "info", "No aliases yet.")
        console.print()
        return
    for entry in masks:
        level = "success" if entry.active else "warn"
        tail = "" if entry.active else "  (inactive)"
        print_status(console, level, entry.address, f"{entry.label}  ·  {entry.anonymous_id}{tail}")
    console.print()


@email_mask_app.command()
def deactivate(ctx: typer.Context, selector: _Selector, apple_id: _AppleId = None) -> None:
    """Stop an alias forwarding mail but keep it in your list (reversible)."""
    print_title(console, "email-mask", "deactivate")
    provider = _provider(ctx, apple_id)
    try:
        target = find_mask(list_masks(provider), selector)
        deactivate_mask(provider, target.anonymous_id)
    except MaskError as exc:
        _fail(exc)
    print_status(console, "success", f"Deactivated {target.address}")
    console.print()


@email_mask_app.command()
def delete(
    ctx: typer.Context,
    selector: _Selector,
    apple_id: _AppleId = None,
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Actually delete (irreversible). Default: dry-run.")
    ] = False,
) -> None:
    """Permanently delete an alias. Dry-run by default; pass --yes to commit (irreversible)."""
    print_title(console, "email-mask", "delete")
    provider = _provider(ctx, apple_id)
    try:
        target = find_mask(list_masks(provider), selector)
        if not yes:
            print_status(
                console,
                "warn",
                f"Would delete {target.address}",
                "Pass --yes to confirm — no undo.",
            )
            console.print()
            return
        delete_mask(provider, target.anonymous_id)
    except MaskError as exc:
        _fail(exc)
    print_status(console, "success", f"Deleted {target.address}")
    console.print()
