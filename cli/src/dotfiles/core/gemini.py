"""GeminiChunksService: list and copy chunked advisor-prompt files."""

from __future__ import annotations

import shutil
import time
from collections.abc import Callable
from pathlib import Path

from dotfiles.core.fsutil import list_dir
from dotfiles.core.models import GeminiChunk
from dotfiles.core.ports import ProcessRunner


class GeminiError(Exception):
    """Raised for missing pbcopy, missing chunk dir, or other Gemini command errors."""


class GeminiChunksService:
    """List and copy Gemini advisor-prompt chunks."""

    def __init__(
        self,
        *,
        runner: ProcessRunner,
        chunks_dir: Path,
        which: Callable[[str], str | None] = shutil.which,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._runner = runner
        self._chunks_dir = chunks_dir
        self._which = which
        self._sleep = sleep

    def chunks(self) -> list[GeminiChunk]:
        """Return chunks sorted lexicographically by filename."""
        if not self._chunks_dir.is_dir():
            raise GeminiError(f"chunk dir not found: {self._chunks_dir}")
        paths = sorted(
            (p for p in list_dir(self._chunks_dir) if p.name.endswith(".md")),
            key=lambda p: p.name,
        )
        result: list[GeminiChunk] = []
        for path in paths:
            content = path.read_text()
            result.append(
                GeminiChunk(
                    name=path.name,
                    char_count=len(content.encode()),
                    content=content,
                )
            )
        return result

    def copy(self, content: str) -> None:
        """Copy content to the macOS clipboard via pbcopy."""
        self._require_pbcopy()
        self._runner.run(("pbcopy",), stdin=content)

    def wait(self, seconds: float) -> None:
        """Sleep for the given duration (injected; used between clipboard copies)."""
        self._sleep(seconds)

    def _require_pbcopy(self) -> None:
        if not self._which("pbcopy"):
            raise GeminiError("pbcopy not available (macOS only)")
