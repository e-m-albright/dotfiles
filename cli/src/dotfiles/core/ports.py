"""Hexagonal ports: the only interfaces the core depends on.

Concrete implementations live in `dotfiles.adapters`; tests inject fakes.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from dotfiles.core.models import CommandResult

# Alias for unstructured external JSON data (LM Studio API responses).
JsonDict = dict[str, Any]


@runtime_checkable
class ProcessRunner(Protocol):
    """Runs external commands. The single subprocess seam for the whole app."""

    def run(
        self,
        command: Sequence[str],
        *,
        check: bool = False,
        env: Mapping[str, str] | None = None,
        stdin: str | None = None,
    ) -> CommandResult: ...


@runtime_checkable
class FileSystem(Protocol):
    """Filesystem reads/writes the core needs (e.g. authorized_keys)."""

    def read_text(self, path: Path) -> str: ...

    def write_text(self, path: Path, content: str) -> None: ...

    def exists(self, path: Path) -> bool: ...

    def mkdir(self, path: Path, *, parents: bool = True) -> None: ...

    def chmod(self, path: Path, mode: int) -> None: ...

    def is_symlink(self, path: Path) -> bool: ...

    def readlink(self, path: Path) -> Path: ...

    def symlink(self, src: Path, dest: Path) -> None: ...

    def is_dir(self, path: Path) -> bool: ...

    def iterdir(self, path: Path) -> list[Path]: ...


@runtime_checkable
class HttpClient(Protocol):
    """HTTP client port — mockable seam for LM Studio API calls."""

    def get_json(self, url: str) -> JsonDict: ...

    def post_json(self, url: str, body: JsonDict) -> JsonDict: ...
