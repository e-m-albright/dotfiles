from pathlib import Path

from dotfiles_cli.adapters.clock import SystemClock
from dotfiles_cli.adapters.filesystem import LocalFileSystem
from dotfiles_cli.adapters.process import SubprocessRunner
from dotfiles_cli.cli.context import AppContext, build_real_context
from dotfiles_cli.core.ports import Clock, FileSystem, ProcessRunner


def test_build_real_context_wires_real_adapters() -> None:
    ctx = build_real_context(interactive=False)
    assert isinstance(ctx.runner, ProcessRunner)
    assert isinstance(ctx.fs, FileSystem)
    assert isinstance(ctx.clock, Clock)
    assert isinstance(ctx.runner, SubprocessRunner)
    assert isinstance(ctx.fs, LocalFileSystem)
    assert isinstance(ctx.clock, SystemClock)
    assert ctx.interactive is False
    assert ctx.home == Path.home()
    assert ctx.settings.default_session == "mobile"


def test_app_context_is_constructible_with_fakes() -> None:
    from datetime import UTC, datetime

    from dotfiles_cli.core.settings import Settings
    from tests.fakes import (
        FakeClock,
        FakeFileSystem,
        FakeHttpClient,
        FakeProcessRunner,
        FakeSessionLauncher,
    )

    ctx = AppContext(
        runner=FakeProcessRunner(),
        fs=FakeFileSystem(),
        clock=FakeClock(datetime(2026, 5, 31, tzinfo=UTC)),
        settings=Settings(),
        interactive=False,
        home=Path("/home/evan"),
        launcher=FakeSessionLauncher(),
        http=FakeHttpClient(),
        dotfiles_dir=Path("/home/evan/dotfiles"),
    )
    assert ctx.home == Path("/home/evan")


def test_real_context_has_launcher() -> None:
    from dotfiles_cli.adapters.launcher import FzfExecLauncher
    from dotfiles_cli.cli.context import build_real_context

    ctx = build_real_context(interactive=False)
    assert isinstance(ctx.launcher, FzfExecLauncher)
