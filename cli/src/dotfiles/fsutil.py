"""Tiny filesystem helpers used in place of the former FileSystem port."""

from pathlib import Path

from dotfiles.logging import get_logger

_log = get_logger(__name__)


def read_text_or(path: Path, default: str = "") -> str:
    """File text, or *default* when the file is missing or unreadable.

    The single definition every probe uses (it had drifted into three private
    ``_read_text`` copies with divergent handling). A genuine read error —
    permissions, a broken mount — is logged so it can't silently masquerade as
    "absent"/"not deployed"; a plain missing file returns *default* quietly.
    """
    try:
        return path.read_text()
    except FileNotFoundError:
        return default
    except OSError as exc:
        _log.warning("read_text_failed", path=str(path), error=str(exc))
        return default


def list_dir(path: Path) -> list[Path]:
    """Return sorted entries under path, or [] if path is not a directory."""
    return sorted(path.iterdir()) if path.is_dir() else []


def subdirs(path: Path, *, include_hidden: bool = False) -> list[Path]:
    """Immediate subdirectories of *path*, excluding hidden/dot dirs by default.

    The single definition of "a counted subdirectory" so the fleet skill-dir
    probe and the skill census agree. Skill dirs are kebab-case (the validator
    forbids leading dots), so a vendor's manager metadata (``.hub``,
    ``.curator_state``, …) is never a skill and must not inflate the count.
    """
    return [
        p for p in list_dir(path) if p.is_dir() and (include_hidden or not p.name.startswith("."))
    ]


def symlink(src: Path, dest: Path) -> None:
    """Create dest -> src symlink, replacing any existing link or file at dest.

    The parent directory is created if missing, so callers don't each repeat the
    mkdir/unlink/symlink dance. The single seam for force-replacing a symlink.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink() or dest.exists():
        dest.unlink()
    dest.symlink_to(src)


def prune_broken_symlinks(directory: Path) -> int:
    """Remove dangling symlinks (target no longer exists) from *directory*.

    Returns the number of links pruned. A no-op returning 0 if *directory* is
    not a directory. Used to clean up agent link dirs before re-linking, so a
    deleted source leaves no orphan behind.
    """
    if not directory.is_dir():
        return 0
    pruned = 0
    for link in directory.iterdir():
        if link.is_symlink() and not link.exists():
            link.unlink()
            pruned += 1
    return pruned
