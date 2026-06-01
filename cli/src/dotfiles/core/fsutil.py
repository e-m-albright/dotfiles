"""Tiny filesystem helpers used in place of the former FileSystem port."""

from pathlib import Path


def list_dir(path: Path) -> list[Path]:
    """Return sorted entries under path, or [] if path is not a directory."""
    return sorted(path.iterdir()) if path.is_dir() else []


def symlink(src: Path, dest: Path) -> None:
    """Create dest -> src symlink, replacing any existing link or file at dest."""
    if dest.is_symlink() or dest.exists():
        dest.unlink()
    dest.symlink_to(src)
