from rich.console import Console

from dotfiles.console import console


def test_console_is_rich() -> None:
    assert isinstance(console, Console)
