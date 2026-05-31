"""Real filesystem implementation of the FileSystem port."""

from pathlib import Path


class LocalFileSystem:
    def read_text(self, path: Path) -> str:
        return path.read_text()

    def write_text(self, path: Path, content: str) -> None:
        path.write_text(content)

    def exists(self, path: Path) -> bool:
        return path.exists()

    def mkdir(self, path: Path, *, parents: bool = True) -> None:
        path.mkdir(parents=parents, exist_ok=True)
