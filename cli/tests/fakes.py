"""In-memory fakes implementing the core ports. Tests only."""

import subprocess
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotfiles.cli.context import AppContext
from dotfiles.core.models import CommandResult
from dotfiles.core.settings import LlmSettings, Settings

_JsonDict = dict[str, Any]


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
        self.symlinks: dict[Path, Path] = {}
        self._children: dict[Path, set[Path]] = {}

    def _register_child(self, path: Path) -> None:
        """Register path as a child of its parent (one level up)."""
        parent = path.parent
        if parent != path:  # avoid root registering itself
            if parent not in self._children:
                self._children[parent] = set()
            self._children[parent].add(path)

    def read_text(self, path: Path) -> str:
        return self._files[path]

    def write_text(self, path: Path, content: str) -> None:
        self._files[path] = content
        self._register_child(path)

    def exists(self, path: Path) -> bool:
        return path in self._files or path in self._dirs or path in self.symlinks

    def mkdir(self, path: Path, *, parents: bool = True) -> None:
        self._dirs.add(path)
        self._register_child(path)

    def chmod(self, path: Path, mode: int) -> None:
        self.modes[path] = mode

    def is_symlink(self, path: Path) -> bool:
        return path in self.symlinks

    def readlink(self, path: Path) -> Path:
        return self.symlinks[path]

    def symlink(self, src: Path, dest: Path) -> None:
        self.symlinks[dest] = src
        self._files[dest] = ""  # exists() is True for a symlink
        self._register_child(dest)

    def is_dir(self, path: Path) -> bool:
        return path in self._dirs

    def iterdir(self, path: Path) -> list[Path]:
        if path not in self._dirs:
            return []
        return list(self._children.get(path, set()))


class FakeHttpClient:
    """Records HTTP calls; returns scripted JSON responses, defaulting to {}."""

    def __init__(self) -> None:
        self.gets: list[str] = []
        self.posts: list[tuple[str, _JsonDict]] = []
        self._get_scripts: dict[str, _JsonDict] = {}
        self._post_scripts: dict[str, _JsonDict] = {}

    def script_get(self, url: str, payload: _JsonDict) -> None:
        self._get_scripts[url] = payload

    def script_post(self, url: str, payload: _JsonDict) -> None:
        self._post_scripts[url] = payload

    def get_json(self, url: str) -> _JsonDict:
        self.gets.append(url)
        return self._get_scripts.get(url, {})

    def post_json(self, url: str, body: _JsonDict) -> _JsonDict:
        self.posts.append((url, body))
        return self._post_scripts.get(url, {})


class FakeMultiPostHttpClient(FakeHttpClient):
    """Returns POST responses in FIFO order, falling back to empty dict."""

    def __init__(self) -> None:
        super().__init__()
        self._post_queue: list[_JsonDict] = []

    def queue_post(self, payload: _JsonDict) -> None:
        self._post_queue.append(payload)

    def post_json(self, url: str, body: _JsonDict) -> _JsonDict:
        self.posts.append((url, body))
        if self._post_queue:
            return self._post_queue.pop(0)
        return {}


class FakeClock:
    """Fixed clock."""

    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        return self._fixed


class FakeSessionLauncher:
    """Records pick/attach calls; returns a scripted selection."""

    def __init__(self, selection: str | None = None) -> None:
        self.selection = selection
        self.picked: list[list[str]] = []
        self.attached: list[list[str]] = []

    def pick(self, options: Sequence[str]) -> str | None:
        self.picked.append(list(options))
        return self.selection

    def attach(self, command: Sequence[str]) -> None:
        self.attached.append(list(command))


def make_fake_context(
    *,
    runner: FakeProcessRunner | None = None,
    fs: FakeFileSystem | None = None,
    interactive: bool = False,
    home: Path | None = None,
    launcher: FakeSessionLauncher | None = None,
    dotfiles_dir: Path | None = None,
    http: FakeHttpClient | None = None,
    llm_settings: LlmSettings | None = None,
) -> AppContext:
    """Build an AppContext backed by fakes for CLI tests."""
    return AppContext(
        runner=runner or FakeProcessRunner(),
        fs=fs or FakeFileSystem(),
        clock=FakeClock(datetime(2026, 5, 31, tzinfo=UTC)),
        settings=Settings(),
        interactive=interactive,
        home=home or Path("/home/evan"),
        launcher=launcher or FakeSessionLauncher(),
        http=http or FakeHttpClient(),
        llm_settings=llm_settings or LlmSettings(),
        dotfiles_dir=dotfiles_dir or Path("/home/evan/dotfiles"),
    )
