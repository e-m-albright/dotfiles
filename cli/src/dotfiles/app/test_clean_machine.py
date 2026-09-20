"""Real diagnostics on an empty home and PATH; no host tools can be invoked."""

import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize(
    ("args", "exit_code", "messages"),
    [
        (("doctor",), 1, ("Core Tools", "Configuration", "missing")),
        (("remote", "status"), 0, ("Tailscale", "not connected", "Paseo", "stopped")),
        (("brew", "stale"), 1, ("No such file or directory", "brew")),
    ],
)
def test_diagnostics_report_missing_prerequisites_without_crashing(
    tmp_path: Path, args: tuple[str, ...], exit_code: int, messages: tuple[str, ...]
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    empty_bin = tmp_path / "bin"
    empty_bin.mkdir()
    result = subprocess.run(
        [sys.executable, "-m", "dotfiles.app.main", *args],
        env={
            "HOME": str(home),
            "PATH": str(empty_bin),
            "DOTFILES_DIR": str(_REPO),
            "NO_COLOR": "1",
            "COLUMNS": "120",
        },
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode == exit_code, output
    assert "Traceback" not in output
    assert all(message in output for message in messages), output
    assert list(home.iterdir()) == []
