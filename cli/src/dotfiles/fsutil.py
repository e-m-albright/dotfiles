"""Tiny filesystem helpers used in place of the former FileSystem port."""

from pathlib import Path


def list_dir(path: Path) -> list[Path]:
    """Return sorted entries under path, or [] if path is not a directory."""
    return sorted(path.iterdir()) if path.is_dir() else []


def symlink(src: Path, dest: Path) -> None:
    """Create dest -> src symlink, replacing any existing link or file at dest.

    The parent directory is created if missing, so callers don't each repeat the
    mkdir/unlink/symlink dance. The single seam for force-replacing a symlink.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink() or dest.exists():
        dest.unlink()
    dest.symlink_to(src)


def prune_broken_symlinks(directory: Path) -> None:
    """Remove dangling symlinks (target no longer exists) from *directory*.

    A no-op if *directory* is not a directory. Used to clean up agent link dirs
    before re-linking, so a deleted source leaves no orphan behind.
    """
    if not directory.is_dir():
        return
    for link in directory.iterdir():
        if link.is_symlink() and not link.exists():
            link.unlink()
