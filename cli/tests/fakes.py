"""In-memory fakes implementing the core ports. Tests only."""

import subprocess
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from dotfiles_cli.cli.context import AppContext
from dotfiles_cli.core.models import CommandResult
from dotfiles_cli.core.settings import Settings


class FakeProcessRunner:
    """Records calls; returns scripted results, defaulting to empty success."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self._scripted: dict[tuple[str, ...], CommandResult] = {}

    def script(
        self,
        command: Sequence[str],
        *,
        exit_code: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        key = tuple(command)
        self._scripted[key] = CommandResult(
            command=key, exit_code=exit_code, stdout=stdout, stderr=stderr
        )

    def run(
        self,
        command: Sequence[str],
        *,
        check: bool = False,
        env: Mapping[str, str] | None = None,
    ) -> CommandResult:
        key = tuple(command)
        self.calls.append(key)
        result = self._scripted.get(
            key, CommandResult(command=key, exit_code=0, stdout="", stderr="")
        )
        if check and result.exit_code != 0:
            raise subprocess.CalledProcessError(
                result.exit_code, list(key), output=result.stdout, stderr=result.stderr
            )
        return result


class FakeFileSystem:
    """In-memory filesystem keyed by Path."""

    def __init__(self) -> None:
        self._files: dict[Path, str] = {}
        self._dirs: set[Path] = set()
        self.modes: dict[Path, int] = {}

    def read_text(self, path: Path) -> str:
        return self._files[path]

    def write_text(self, path: Path, content: str) -> None:
        self._files[path] = content

    def exists(self, path: Path) -> bool:
        return path in self._files or path in self._dirs

    def mkdir(self, path: Path, *, parents: bool = True) -> None:
        self._dirs.add(path)

    def chmod(self, path: Path, mode: int) -> None:
        self.modes[path] = mode


class FakeClock:
    """Fixed clock."""

    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        return self._fixed


def make_fake_context(
    *,
    runner: "FakeProcessRunner | None" = None,
    fs: "FakeFileSystem | None" = None,
    interactive: bool = False,
    home: Path | None = None,
):
    """Build an AppContext backed by fakes for CLI tests."""
    return AppContext(
        runner=runner or FakeProcessRunner(),
        fs=fs or FakeFileSystem(),
        clock=FakeClock(datetime(2026, 5, 31, tzinfo=UTC)),
        settings=Settings(),
        interactive=interactive,
        home=home or Path("/home/evan"),
    )
