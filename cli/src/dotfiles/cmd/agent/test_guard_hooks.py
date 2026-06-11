"""Behavioral vector tests for the destructive-shell guard hook.

``ai/agents/shared/hooks/guard-destructive-shell.sh`` is the fleet's safety
floor — deployed verbatim to every hook-capable vendor to block destructive
shell/git commands. Before this suite it was only verified to be *wired*, never
to actually *block*. These tests pipe real command strings through the guard as
the harness would (JSON on stdin) and assert the exit code: 2 = block, 0 = allow.

Run under ``just check``; no bats dependency. The vectors are the contract — add
a bypass here the moment one is found, then make the guard pass it.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[5]
_GUARD = _REPO / "ai" / "agents" / "shared" / "hooks" / "guard-destructive-shell.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("jq") is None,
    reason="guard hook needs bash + jq",
)


def _run(command: str) -> int:
    """Pipe *command* through the guard the way a PreToolUse hook would."""
    payload = json.dumps({"tool_input": {"command": command}})
    result = subprocess.run(
        ["bash", str(_GUARD)],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode


# Commands the guard MUST block (exit 2). Includes the flag-order / quoting
# bypasses that the original literal-substring matcher let through.
BLOCK = [
    "rm -rf /",
    "rm -rf ~",
    "rm -rf $HOME",
    "rm -fr /",  # bypass: flag order
    "rm -r -f /",  # bypass: separated flags
    "rm -Rf ~",  # bypass: capital R
    'rm -rf "$HOME"',  # bypass: quoted home
    "rm -rf ${HOME}",  # bypass: braced home
    "rm --recursive --force /",  # bypass: long flags
    "rm -rf /usr/local/bin",  # absolute root-anchored recursive delete
    "sudo rm -rf /tmp/x",
    "sudo dd if=/dev/zero of=/dev/disk0",
    "git push --force origin main",
    "git push -f origin main",
    "git reset --hard HEAD~1",
    "git clean -fd",
    "git branch -D feature",
    "git commit --no-verify -m x",
    "cd /tmp && rm -rf $HOME/data",  # destructive rm after a compound command
]

# Commands the guard MUST allow (exit 0) — no over-blocking.
ALLOW = [
    "rm -rf ./build",
    "rm -rf node_modules",
    "rm -rf dist",
    "rm file.txt",
    "ls -la /",
    "git push origin main",
    "git push --force-with-lease origin main",
    "git reset --soft HEAD~1",
    "git clean -n",  # dry run
    "git commit -m 'fix'",
]


@pytest.mark.parametrize("command", BLOCK)
def test_guard_blocks(command: str) -> None:
    assert _run(command) == 2, f"guard should BLOCK: {command!r}"


@pytest.mark.parametrize("command", ALLOW)
def test_guard_allows(command: str) -> None:
    assert _run(command) == 0, f"guard should ALLOW: {command!r}"
