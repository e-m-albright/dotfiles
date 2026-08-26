from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).with_name("link_utils.sh")


def _link(source: Path, destination: Path) -> subprocess.CompletedProcess[str]:
    command = f"""
set -euo pipefail
print_skip() {{ :; }}
print_step() {{ :; }}
print_warn() {{ printf '%s\\n' "$1"; }}
source {shlex.quote(str(SCRIPT))}
safe_link {shlex.quote(str(source))} {shlex.quote(str(destination))}
"""
    return subprocess.run(["bash", "-c", command], check=True, capture_output=True, text=True)


def test_safe_link_preserves_regular_file_before_linking(tmp_path: Path) -> None:
    source = tmp_path / "tracked"
    source.write_text("managed")
    destination = tmp_path / "config"
    destination.write_text("local")

    result = _link(source, destination)

    assert destination.is_symlink()
    assert destination.resolve() == source
    backups = list(tmp_path.glob("config.backup-*"))
    assert len(backups) == 1
    assert backups[0].read_text() == "local"
    assert "Preserved existing config" in result.stdout


def test_safe_link_preserves_directory_instead_of_linking_inside_it(tmp_path: Path) -> None:
    source = tmp_path / "tracked"
    source.write_text("managed")
    destination = tmp_path / "config"
    destination.mkdir()
    (destination / "local").write_text("keep")

    _link(source, destination)

    assert destination.is_symlink()
    backups = list(tmp_path.glob("config.backup-*"))
    assert len(backups) == 1
    assert (backups[0] / "local").read_text() == "keep"


def test_safe_link_is_idempotent_for_the_managed_target(tmp_path: Path) -> None:
    source = tmp_path / "tracked"
    source.write_text("managed")
    destination = tmp_path / "config"

    _link(source, destination)
    _link(source, destination)

    assert destination.is_symlink()
    assert list(tmp_path.glob("config.backup-*")) == []
