"""In-memory fakes implementing application ports. Tests only."""

import subprocess
import threading
from collections.abc import Mapping, Sequence
from pathlib import Path

from dotfiles.adapters.ports import CommandResult
from dotfiles.app.context import AppContext


class FakeProcessRunner:
    """Records calls; returns scripted results, defaulting to empty success."""

    def __init__(self) -> None:
        # Doctor fans sections out across threads; guard the recorded state so
        # concurrent callers can't interleave a single call's appends.
        self._lock = threading.Lock()
        self.calls: list[tuple[str, ...]] = []
        self.calls_with_input: list[tuple[tuple[str, ...], str | None]] = []
        self.inputs: list[str | None] = []
        self.capture_output: list[bool] = []
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
        stdin: str | None = None,
        cwd: Path | None = None,
        capture_output: bool = True,
    ) -> CommandResult:
        key = tuple(command)
        with self._lock:
            self.calls.append(key)
            self.inputs.append(stdin)
            self.capture_output.append(capture_output)
            self.calls_with_input.append((key, stdin))
        result = self._scripted.get(
            key, CommandResult(command=key, exit_code=0, stdout="", stderr="")
        )
        if check and result.exit_code != 0:
            raise subprocess.CalledProcessError(
                result.exit_code, list(key), output=result.stdout, stderr=result.stderr
            )
        return result


def write_tree(base: Path, spec: dict[str, str | None]) -> None:
    """Create files/dirs under base. value=str writes a file; value=None makes a dir."""
    for rel, content in spec.items():
        target = base / rel
        if content is None:
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)


def make_fake_context(
    *,
    runner: FakeProcessRunner | None = None,
    home: Path | None = None,
    dotfiles_dir: Path | None = None,
) -> AppContext:
    """Build an AppContext backed by fakes for CLI tests."""
    home_path = home or Path("/home/evan")
    return AppContext(
        runner=runner or FakeProcessRunner(),
        home=home_path,
        dotfiles_dir=dotfiles_dir or Path("/home/evan/dotfiles"),
    )
