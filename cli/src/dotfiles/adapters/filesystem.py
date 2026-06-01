"""Real filesystem implementation of the FileSystem port."""

from pathlib import Path


class LocalFileSystem:
    """Real filesystem implementation of the FileSystem port."""

    def read_text(self, path: Path) -> str:
        return path.read_text()

    def write_text(self, path: Path, content: str) -> None:
        path.write_text(content)

    def exists(self, path: Path) -> bool:
        return path.exists()

    def mkdir(self, path: Path, *, parents: bool = True) -> None:
        path.mkdir(parents=parents, exist_ok=True)

    def chmod(self, path: Path, mode: int) -> None:
        path.chmod(mode)

    def is_symlink(self, path: Path) -> bool:
        return path.is_symlink()

    def readlink(self, path: Path) -> Path:
        return path.readlink()

    def symlink(self, src: Path, dest: Path) -> None:
        if dest.is_symlink() or dest.exists():
            dest.unlink()
        dest.symlink_to(src)

    def is_dir(self, path: Path) -> bool:
        return path.is_dir()

    def iterdir(self, path: Path) -> list[Path]:
        if not path.is_dir():
            return []
        return list(path.iterdir())
