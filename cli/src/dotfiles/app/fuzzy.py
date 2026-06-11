"""Conservative fuzzy command resolution for the dotfiles CLI.

When a subcommand isn't an exact match, resolve it to the *single* closest known
command — a singular/plural variant, a unique prefix, or a one-character typo — and
only when exactly one candidate qualifies. Ambiguous or distant input falls through
to Typer's normal "no such command" error. So `dotfiles agents` runs `agent` and
`dotfiles agent overviw` runs `overview`, but `dotfiles agent s` still errs (three
commands start with "s"). The resolution is announced on stderr so the real name is
learnable, and never touches stdout.
"""

from __future__ import annotations

import typer
from typer._click.core import Command, Context
from typer.core import TyperGroup


def _within_one_edit(typed: str, command: str) -> bool:
    """True when *typed* is *command* with at most one char added/removed/changed."""
    if abs(len(typed) - len(command)) > 1:
        return False
    if len(typed) == len(command):
        return sum(a != b for a, b in zip(typed, command, strict=True)) <= 1
    short, long = sorted((typed, command), key=len)
    return any(short == long[:i] + long[i + 1 :] for i in range(len(long)))


def closest_command(typed: str, commands: list[str]) -> str | None:
    """The one command *typed* most likely means, or None if it isn't unambiguous.

    Tiers, most-confident first; the first tier with exactly one match wins.
    """
    if not typed:
        return None
    typed = typed.lower()
    toggled = typed[:-1] if typed.endswith("s") else typed + "s"
    if toggled in commands:
        return toggled
    by_prefix = [c for c in commands if c.startswith(typed)]
    if len(by_prefix) == 1:
        return by_prefix[0]
    by_typo = [c for c in commands if _within_one_edit(typed, c)]
    if len(by_typo) == 1:
        return by_typo[0]
    return None


class FuzzyTyperGroup(TyperGroup):
    """A Typer group that resolves a near-miss subcommand to its single best match."""

    def get_command(self, ctx: Context, cmd_name: str) -> Command | None:
        exact = super().get_command(ctx, cmd_name)
        if exact is not None:
            return exact
        match = closest_command(cmd_name, self.list_commands(ctx))
        if match is None:
            return None
        typer.echo(f"dotfiles: '{cmd_name}' → '{match}'", err=True)
        return super().get_command(ctx, match)
