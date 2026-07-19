"""Filesystem operation shared by host-configuration checks."""

from pathlib import Path


def symlink(src: Path, dest: Path) -> None:
    """Create dest -> src symlink, replacing any existing link or file at dest.

    The parent directory is created if missing, so callers don't each repeat the
    mkdir/unlink/symlink dance. The single seam for force-replacing a symlink.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink() or dest.exists():
        dest.unlink()
    dest.symlink_to(src)
