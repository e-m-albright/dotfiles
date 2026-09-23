from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
PROFILE_STATUS = ROOT / "shell/profile-status.zsh"


def _render(detail: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            "-c",
            'DOTFILES_STARTUP_DETAIL=off; source "$1"; profile_status "$2"',
            "profile-status-test",
            str(PROFILE_STATUS),
            detail,
        ],
        env={**os.environ, "DOTFILES_PROFILE": "work", "TERM": "dumb"},
        capture_output=True,
        text=True,
        check=False,
    )


def test_option_delete_has_explicit_zsh_word_binding() -> None:
    zshrc = (ROOT / "shell/.zshrc").read_text()

    assert "bindkey '^[^?' backward-kill-word" in zshrc
    assert "bindkey '^[^H' backward-kill-word" in zshrc


def test_short_profile_status_is_compact_and_actionable() -> None:
    result = _render("short")

    assert result.returncode == 0
    assert result.stdout == "dotfiles / profile=work  (profile_status for more)\n"


def test_medium_profile_status_explains_policy_without_tool_inventory() -> None:
    result = _render("medium")

    assert result.returncode == 0
    assert "shell:" in result.stdout
    assert "agents:" in result.stdout
    assert "data:" in result.stdout
    assert "runtimes:" in result.stdout
    assert "brew       " not in result.stdout


def test_long_profile_status_adds_tool_inventory_and_config_root() -> None:
    result = _render("long")

    assert result.returncode == 0
    assert "brew       " in result.stdout
    assert "claude     " in result.stdout
    assert "config:" in result.stdout
