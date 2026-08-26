from pathlib import Path

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.adapters.process import SubprocessRunner
from dotfiles.app.context import AppContext, build_real_context


def test_build_real_context_wires_real_adapters() -> None:
    ctx = build_real_context()
    assert isinstance(ctx.runner, ProcessRunner)
    assert isinstance(ctx.runner, SubprocessRunner)
    assert ctx.home == Path.home()


def test_app_context_is_constructible_with_fakes() -> None:
    from dotfiles.testing.fakes import FakeProcessRunner

    ctx = AppContext(
        runner=FakeProcessRunner(),
        home=Path("/home/evan"),
        dotfiles_dir=Path("/home/evan/dotfiles"),
    )
    assert ctx.home == Path("/home/evan")
