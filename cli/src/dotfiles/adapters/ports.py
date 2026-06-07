"""Hexagonal ports + their payloads: the I/O seams the rest of the app depends on.

Concrete implementations live alongside this module in `dotfiles.adapters`; tests
inject fakes. `CommandResult` lives here because it's the `ProcessRunner` payload.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

# Alias for unstructured external JSON data (LM Studio API responses).
JsonDict = dict[str, Any]


class CommandResult(BaseModel):
    """Result of running an external command via a ProcessRunner port."""

    model_config = ConfigDict(frozen=True)

    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


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
        cwd: Path | None = None,
    ) -> CommandResult: ...


@runtime_checkable
class HttpClient(Protocol):
    """HTTP client port — mockable seam for LM Studio API calls."""

    def get_json(self, url: str) -> JsonDict: ...

    def post_json(self, url: str, body: JsonDict) -> JsonDict: ...
