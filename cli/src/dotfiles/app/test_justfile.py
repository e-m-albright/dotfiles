"""Exercise cleanup recipes only in a disposable repository with fail-closed tools."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("mode", [None, "--caches", "--artifacts", "all"])
def test_scrub_defaults_to_caches_and_requires_explicit_artifact_cleanup(
    tmp_path: Path, mode: str | None
) -> None:
    just = shutil.which("just")
    assert just, "just is required to verify cleanup recipes"
    repo = tmp_path / "repository"
    repo.mkdir()
    (repo / "cli").mkdir()
    (repo / "justfile").write_text((_REPO / "justfile").read_text())
    artifact = repo / "docs/plans/decision.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("Keep this authored decision unless artifacts were explicitly selected.")
    history = repo / ".crush/session.db"
    history.parent.mkdir()
    history.write_text("Synthetic agent history, not a cache")
    cache = repo / "cli/.pytest_cache/cached"
    cache.parent.mkdir()
    cache.write_text("Disposable cache")
    stubs = tmp_path / "bin"
    stubs.mkdir()
    (stubs / "bash").symlink_to("/bin/bash")
    remover = stubs / "rm"
    remover.write_text(
        f"#!{sys.executable}\n"
        "import pathlib, shutil, sys\n"
        f"root = pathlib.Path({json.dumps(str(repo))}).resolve()\n"
        "assert sys.argv[1] == '-rf'\n"
        "paths = [pathlib.Path(arg) for arg in sys.argv[2:]]\n"
        "assert all(p.resolve().is_relative_to(root) and p.resolve() != root for p in paths)\n"
        "for p in paths:\n"
        "    if p.is_dir(): shutil.rmtree(p)\n"
        "    elif p.exists(): p.unlink()\n"
    )
    remover.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    result = subprocess.run(
        [just, "--justfile", str(repo / "justfile"), "scrub", *([mode] if mode else [])],
        cwd=repo,
        env={"HOME": str(home), "PATH": str(stubs)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert artifact.exists() is (mode not in {"--artifacts", "all"})
    assert cache.exists() is (mode == "--artifacts")
    assert history.read_text() == "Synthetic agent history, not a cache"
