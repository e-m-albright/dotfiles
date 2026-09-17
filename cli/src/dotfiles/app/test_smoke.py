import dotfiles


def test_package_imports() -> None:
    assert dotfiles.__doc__ is not None
