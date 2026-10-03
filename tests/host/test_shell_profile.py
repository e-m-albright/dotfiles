"""Profiling must still report timing when the shell being diagnosed fails."""

import subprocess
from pathlib import Path

import pytest

ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "AGENTS.md").is_file()
)


@pytest.mark.parametrize("exit_code", [0, 7])
def test_profiling_reports_all_timings_despite_startup_failure(
    tmp_path: Path, exit_code: int
) -> None:
    binaries = tmp_path / "bin"
    binaries.mkdir()
    zsh = binaries / "zsh"
    zsh.write_text(f"#!/bin/bash\nexit {exit_code}\n")
    zsh.chmod(0o755)
    home = tmp_path / "home with spaces"
    home.mkdir()
    for name in (".zshenv", ".zprofile", ".zshrc"):
        (home / name).write_text("return 7\n")

    result = subprocess.run(
        ["/bin/bash", str(ROOT / "scripts/profile-shell.sh")],
        env={"HOME": str(home), "PATH": f"{binaries}:/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    assert "Total startup time:" in result.stdout
    for name in (".zshenv", ".zprofile", ".zshrc"):
        assert name in result.stdout
    assert "Tip:" in result.stdout
