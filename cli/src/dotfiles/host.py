"""Host intent shared by bootstrap, maintenance, and diagnostics."""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
Profile = Literal["personal", "work"]


def resolve_profile(home: Path, explicit: str | None = None) -> Profile:
    """Explicit selection wins, then the persisted marker, then shell/default."""
    marker = home / ".config/dotfiles/profile"
    selected = explicit
    if selected is None:
        selected = (
            marker.read_text().rstrip("\n")
            if marker.exists()
            else os.getenv("DOTFILES_PROFILE", "personal")
        )
    if selected not in {"personal", "work"}:
        raise ValueError(f"Invalid host profile: {selected!r}; expected personal or work")
    return cast("Profile", selected)


@dataclass(frozen=True)
class RuntimeVersions:
    node: str
    python: str
    pnpm: str

    @classmethod
    def load(cls, path: Path = REPO_ROOT / "config/runtimes.conf") -> "RuntimeVersions":
        values: dict[str, str] = {}
        for line in path.read_text().splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            match = re.fullmatch(
                r"(NODE_VERSION|PYTHON_VERSION|PNPM_VERSION)=([0-9]+(?:\.[0-9]+)*)", line
            )
            if not match or match[1] in values:
                raise ValueError(f"Invalid runtime declaration: {line!r}")
            values[match[1]] = match[2]
        if set(values) != {"NODE_VERSION", "PYTHON_VERSION", "PNPM_VERSION"}:
            raise ValueError("Missing runtime declarations")
        return cls(values["NODE_VERSION"], values["PYTHON_VERSION"], values["PNPM_VERSION"])


RUNTIMES = RuntimeVersions.load()


@dataclass(frozen=True)
class ManagedLink:
    profiles: tuple[str, ...]
    label: str
    source: str
    destination: str
    required_tool: str


def managed_links(path: Path = REPO_ROOT / "config/links.tsv") -> list[ManagedLink]:
    links: list[ManagedLink] = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        profiles, label, source, destination, tool = line.split("\t")
        links.append(ManagedLink(tuple(profiles.split(",")), label, source, destination, tool))
    return links
