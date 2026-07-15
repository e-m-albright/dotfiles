from pathlib import Path

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.adapters.process import SubprocessRunner
from dotfiles.app.context import AppContext, build_real_context


def test_build_real_context_wires_real_adapters() -> None:
    ctx = build_real_context(interactive=False)
    assert isinstance(ctx.runner, ProcessRunner)
    assert isinstance(ctx.runner, SubprocessRunner)
    assert ctx.interactive is False
    assert ctx.home == Path.home()
    assert ctx.settings.default_session == "mobile"


def test_app_context_is_constructible_with_fakes() -> None:
    from dotfiles.settings import Settings
    from dotfiles.testing.fakes import (
        FakeProcessRunner,
        FakeSessionLauncher,
    )

    ctx = AppContext(
        runner=FakeProcessRunner(),
        settings=Settings(),
        interactive=False,
        home=Path("/home/evan"),
        launcher=FakeSessionLauncher(),
        dotfiles_dir=Path("/home/evan/dotfiles"),
    )
    assert ctx.home == Path("/home/evan")


def test_real_context_has_launcher() -> None:
    from dotfiles.adapters.launcher import FzfExecLauncher
    from dotfiles.app.context import build_real_context

    ctx = build_real_context(interactive=False)
    assert isinstance(ctx.launcher, FzfExecLauncher)
