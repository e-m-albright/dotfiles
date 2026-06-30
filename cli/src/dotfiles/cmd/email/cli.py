"""`dotfiles email` commands: generate iCloud Hide My Email aliases from the terminal."""

from __future__ import annotations

from typing import Annotated

import typer

from dotfiles.app.context import app_context
from dotfiles.app.fuzzy import FuzzyTyperGroup
from dotfiles.cmd.email.service import MaskError, copy_to_clipboard, create_mask
from dotfiles.console import console, print_field, print_status, print_title

email_app = typer.Typer(cls=FuzzyTyperGroup, help="Generate iCloud Hide My Email aliases.")


@email_app.command()
def mask(
    ctx: typer.Context,
    label: Annotated[
        str, typer.Argument(help="Label to file the alias under in iCloud settings.")
    ] = "dotfiles",
    apple_id: Annotated[
        str | None,
        typer.Option("--apple-id", help="iCloud account (defaults to $DOTFILES_APPLE_ID)."),
    ] = None,
    copy: Annotated[
        bool, typer.Option("--copy/--no-copy", help="Copy the new address to the clipboard.")
    ] = True,
) -> None:
    """Generate a fresh Hide My Email alias, reserve it, and copy it to the clipboard.

    First run prompts (once) for the iCloud password and a two-factor code, then
    persists the session — subsequent runs are non-interactive. Requires iCloud+.
    """
    app_ctx = app_context(ctx)
    account = apple_id or app_ctx.settings.apple_id
    print_title(console, "email", "mask")
    if not account:
        print_status(
            console,
            "error",
            "No iCloud account set.",
            "Pass --apple-id you@icloud.com or set DOTFILES_APPLE_ID.",
        )
        raise typer.Exit(code=1)

    try:
        provider = app_ctx.mask_provider_factory(account)
        reserved = create_mask(provider, label)
    except MaskError as exc:
        print_status(console, "error", str(exc))
        raise typer.Exit(code=1) from exc

    print_status(console, "success", "New Hide My Email created")
    print_field(console, "address", reserved.address, soft_wrap=True)
    print_field(console, "label", reserved.label)
    if copy and copy_to_clipboard(app_ctx.runner, reserved.address):
        print_status(console, "info", "Copied to clipboard")
    console.print()
