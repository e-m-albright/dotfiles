"""Tests for GeminiChunksService (core/gemini.py)."""

from pathlib import Path

import pytest

from dotfiles.core.gemini import GeminiChunksService, GeminiError
from tests.fakes import FakeFileSystem, FakeProcessRunner

_CHUNKS_DIR = Path("/home/evan/dotfiles/prompts/gemini-chunks")


def _make_fs(*chunks: tuple[str, str]) -> FakeFileSystem:
    """Return a FakeFileSystem with the given (name, content) chunk files."""
    fs = FakeFileSystem()
    fs.mkdir(_CHUNKS_DIR)
    for name, content in chunks:
        fs.write_text(_CHUNKS_DIR / name, content)
    return fs


def _make_service(
    fs: FakeFileSystem,
    runner: FakeProcessRunner | None = None,
    which_result: str | None = "/usr/bin/pbcopy",
    sleep_calls: list[float] | None = None,
) -> tuple[GeminiChunksService, FakeProcessRunner]:
    r = runner or FakeProcessRunner()
    captured_sleeps: list[float] = sleep_calls if sleep_calls is not None else []

    def fake_sleep(n: float) -> None:
        captured_sleeps.append(n)

    svc = GeminiChunksService(
        fs=fs,
        runner=r,
        chunks_dir=_CHUNKS_DIR,
        which=lambda _name: which_result,
        sleep=fake_sleep,
    )
    return svc, r


# ---------------------------------------------------------------------------
# chunks()
# ---------------------------------------------------------------------------


def test_chunks_returns_sorted_by_name() -> None:
    fs = _make_fs(("03-c.md", "ccc"), ("01-a.md", "a"), ("02-b.md", "bb"))
    svc, _ = _make_service(fs)
    names = [c.name for c in svc.chunks()]
    assert names == ["01-a.md", "02-b.md", "03-c.md"]


def test_chunks_char_count_is_byte_length() -> None:
    # ASCII: len == byte len; add a multi-byte char to confirm bytes used.
    content = "hello"  # 5 bytes
    fs = _make_fs(("01-x.md", content))
    svc, _ = _make_service(fs)
    chunk = svc.chunks()[0]
    assert chunk.char_count == len(content.encode())


def test_chunks_multibyte_char_count() -> None:
    content = "café"  # é is 2 bytes in UTF-8 → 5 bytes total
    fs = _make_fs(("01-x.md", content))
    svc, _ = _make_service(fs)
    chunk = svc.chunks()[0]
    assert chunk.char_count == len(content.encode())  # 5


def test_chunks_content_roundtrips() -> None:
    fs = _make_fs(("01-x.md", "some content\n"))
    svc, _ = _make_service(fs)
    assert svc.chunks()[0].content == "some content\n"


def test_chunks_missing_dir_raises_gemini_error() -> None:
    fs = FakeFileSystem()  # no dir created
    svc, _ = _make_service(fs)
    with pytest.raises(GeminiError, match="chunk dir not found"):
        svc.chunks()


def test_chunks_ignores_non_md_files() -> None:
    fs = _make_fs(("01-a.md", "aa"), ("README.txt", "ignore me"))
    svc, _ = _make_service(fs)
    assert len(svc.chunks()) == 1
    assert svc.chunks()[0].name == "01-a.md"


# ---------------------------------------------------------------------------
# copy()
# ---------------------------------------------------------------------------


def test_copy_calls_pbcopy_with_content_as_stdin() -> None:
    fs = _make_fs(("01-a.md", "hello"))
    svc, runner = _make_service(fs)
    svc.copy("hello")
    assert runner.calls == [("pbcopy",)]
    assert runner.inputs == ["hello"]


def test_copy_missing_pbcopy_raises_gemini_error() -> None:
    fs = _make_fs(("01-a.md", "hello"))
    svc, _ = _make_service(fs, which_result=None)
    with pytest.raises(GeminiError, match="pbcopy not available"):
        svc.copy("hello")
