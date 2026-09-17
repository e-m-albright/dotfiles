from pathlib import Path

from dotfiles.adapters.keychain import MacOSKeychainStore
from dotfiles.adapters.ports import KeychainStore, ProcessRunner
from dotfiles.adapters.process import SubprocessRunner
from dotfiles.app.context import AppContext, build_real_context


def test_build_real_context_wires_real_adapters() -> None:
    ctx = build_real_context()
    assert isinstance(ctx.runner, ProcessRunner)
    assert isinstance(ctx.runner, SubprocessRunner)
    assert isinstance(ctx.keychain, KeychainStore)
    assert isinstance(ctx.keychain, MacOSKeychainStore)
    assert ctx.home == Path.home()


def test_app_context_is_constructible_with_fakes() -> None:
    from dotfiles.testing.fakes import FakeKeychainStore, FakeProcessRunner

    ctx = AppContext(
        runner=FakeProcessRunner(),
        keychain=FakeKeychainStore(),
        home=Path("/home/tester"),
        dotfiles_dir=Path("/home/tester/dotfiles"),
    )
    assert ctx.home == Path("/home/tester")
