"""Tests for GeminiChunksService (core/gemini.py)."""

from pathlib import Path

import pytest

from dotfiles.cmd.agent.web_chat import GeminiChunksService, GeminiError
from dotfiles.testing.fakes import FakeProcessRunner


def _make_chunks_dir(tmp_path: Path, *chunks: tuple[str, str]) -> Path:
    """Create a chunks dir under tmp_path with the given (name, content) files."""
    chunks_dir = tmp_path / "gemini-chunks"
    chunks_dir.mkdir()
    for name, content in chunks:
        (chunks_dir / name).write_text(content)
    return chunks_dir


def _make_service(
    chunks_dir: Path,
    runner: FakeProcessRunner | None = None,
    which_result: str | None = "/usr/bin/pbcopy",
    sleep_calls: list[float] | None = None,
) -> tuple[GeminiChunksService, FakeProcessRunner]:
    r = runner or FakeProcessRunner()
    captured_sleeps: list[float] = sleep_calls if sleep_calls is not None else []

    def fake_sleep(n: float) -> None:
        captured_sleeps.append(n)

    svc = GeminiChunksService(
        runner=r,
        chunks_dir=chunks_dir,
        which=lambda _name: which_result,
        sleep=fake_sleep,
    )
    return svc, r


# ---------------------------------------------------------------------------
# chunks()
# ---------------------------------------------------------------------------


def test_chunks_returns_sorted_by_name(tmp_path: Path) -> None:
    chunks_dir = _make_chunks_dir(tmp_path, ("03-c.md", "ccc"), ("01-a.md", "a"), ("02-b.md", "bb"))
    svc, _ = _make_service(chunks_dir)
    names = [c.name for c in svc.chunks()]
    assert names == ["01-a.md", "02-b.md", "03-c.md"]


def test_chunks_char_count_is_byte_length(tmp_path: Path) -> None:
    # ASCII: len == byte len; add a multi-byte char to confirm bytes used.
    content = "hello"  # 5 bytes
    chunks_dir = _make_chunks_dir(tmp_path, ("01-x.md", content))
    svc, _ = _make_service(chunks_dir)
    chunk = svc.chunks()[0]
    assert chunk.char_count == len(content.encode())


def test_chunks_multibyte_char_count(tmp_path: Path) -> None:
    content = "café"  # é is 2 bytes in UTF-8 → 5 bytes total
    chunks_dir = _make_chunks_dir(tmp_path, ("01-x.md", content))
    svc, _ = _make_service(chunks_dir)
    chunk = svc.chunks()[0]
    assert chunk.char_count == len(content.encode())  # 5


def test_chunks_content_roundtrips(tmp_path: Path) -> None:
    chunks_dir = _make_chunks_dir(tmp_path, ("01-x.md", "some content\n"))
    svc, _ = _make_service(chunks_dir)
    assert svc.chunks()[0].content == "some content\n"


def test_chunks_missing_dir_raises_gemini_error(tmp_path: Path) -> None:
    svc, _ = _make_service(tmp_path / "nonexistent")
    with pytest.raises(GeminiError, match="chunk dir not found"):
        svc.chunks()


def test_chunks_ignores_non_md_files(tmp_path: Path) -> None:
    chunks_dir = _make_chunks_dir(tmp_path, ("01-a.md", "aa"), ("README.txt", "ignore me"))
    svc, _ = _make_service(chunks_dir)
    assert len(svc.chunks()) == 1
    assert svc.chunks()[0].name == "01-a.md"


# ---------------------------------------------------------------------------
# copy()
# ---------------------------------------------------------------------------


def test_copy_calls_pbcopy_with_content_as_stdin(tmp_path: Path) -> None:
    chunks_dir = _make_chunks_dir(tmp_path, ("01-a.md", "hello"))
    svc, runner = _make_service(chunks_dir)
    svc.copy("hello")
    assert runner.calls == [("pbcopy",)]
    assert runner.inputs == ["hello"]


def test_copy_missing_pbcopy_raises_gemini_error(tmp_path: Path) -> None:
    chunks_dir = _make_chunks_dir(tmp_path, ("01-a.md", "hello"))
    svc, _ = _make_service(chunks_dir, which_result=None)
    with pytest.raises(GeminiError, match="pbcopy not available"):
        svc.copy("hello")
