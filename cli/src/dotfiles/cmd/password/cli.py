"""`dotfiles password` - generate a random password and copy it to the clipboard."""

from __future__ import annotations

from typing import Annotated

import typer

from dotfiles.app.context import app_context
from dotfiles.cmd.password.service import DEFAULT_LENGTH, copy_to_clipboard, generate_password
from dotfiles.console import console, print_field, print_status, print_title


def password_command(
    ctx: typer.Context,
    length: Annotated[
        int, typer.Argument(min=1, max=256, help="Password length in characters.")
    ] = DEFAULT_LENGTH,
    copy: Annotated[
        bool, typer.Option("--copy/--no-copy", help="Copy the password to the clipboard.")
    ] = True,
) -> None:
    """Generate a random alphanumeric password (20 chars by default) and copy it."""
    print_title(console, "password")
    password = generate_password(length)
    print_field(console, "password", password, soft_wrap=True)
    if copy and copy_to_clipboard(app_context(ctx).runner, password):
        print_status(console, "info", "Copied to clipboard")
    console.print()
