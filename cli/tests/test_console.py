from rich.console import Console

from dotfiles_cli.console import console, err_console


def test_consoles_are_rich_and_distinct() -> None:
    assert isinstance(console, Console)
    assert isinstance(err_console, Console)
    assert err_console.stderr is True
    assert console.stderr is False
