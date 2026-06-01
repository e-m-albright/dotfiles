from datetime import datetime
from pathlib import Path

from dotfiles_cli.adapters.clock import SystemClock
from dotfiles_cli.adapters.filesystem import LocalFileSystem
from dotfiles_cli.core.ports import Clock, FileSystem


def test_local_filesystem_satisfies_port() -> None:
    assert isinstance(LocalFileSystem(), FileSystem)


def test_local_filesystem_roundtrip(tmp_path: Path) -> None:
    fs = LocalFileSystem()
    target = tmp_path / "nested" / "file.txt"
    assert fs.exists(target) is False
    fs.mkdir(target.parent)
    fs.write_text(target, "hello\n")
    assert fs.exists(target) is True
    assert fs.read_text(target) == "hello\n"


def test_system_clock_satisfies_port_and_returns_datetime() -> None:
    clock = SystemClock()
    assert isinstance(clock, Clock)
    assert isinstance(clock.now(), datetime)
    assert clock.now().tzinfo is not None


def test_local_filesystem_symlink_ops(tmp_path: Path) -> None:
    fs = LocalFileSystem()
    target = tmp_path / "target.txt"
    fs.write_text(target, "hi")
    link = tmp_path / "link.txt"
    assert fs.is_symlink(link) is False
    fs.symlink(target, link)
    assert fs.is_symlink(link) is True
    assert fs.readlink(link) == target
