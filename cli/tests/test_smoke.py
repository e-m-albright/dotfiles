from dotfiles_cli import __version__


def test_package_imports_and_has_version() -> None:
    assert __version__ == "0.1.0"
