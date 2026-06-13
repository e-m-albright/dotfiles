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
_HOOKS = _REPO / "ai" / "agents" / "shared" / "hooks"
_GUARD = _HOOKS / "guard-destructive-shell.sh"
_GUARD_FILE = _HOOKS / "guard-sensitive-file.sh"

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
    "git push -f",  # bypass: bare -f, no trailing arg (regex required trailing space)
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


def _run_file(path: str) -> int:
    """Pipe a target file path through the sensitive-file guard."""
    payload = json.dumps({"tool_input": {"file_path": path}})
    result = subprocess.run(
        ["bash", str(_GUARD_FILE)],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode


# Sensitive files the guard MUST block. The bare/relative env files were the
# bypass: the old */.env globs required a leading slash.
BLOCK_FILE = [
    ".env",  # bypass: bare, no leading dir
    ".env.local",  # bypass: the most common secret file
    "proj/.env",
    "config/.env.production",
    ".aws/credentials",
    "id_rsa",
    "id_ed25519",
    "deploy.pem",
    "cert.p12",
    "config/secrets.json",
    "k8s/secrets.yaml",
    ".npmrc",
    ".netrc",
    "service-account.json",  # GCP service-account key
    "gcp-service_account.json",
    "token.json",  # OAuth token store
    "creds/oauth_token.json",
    "gha-creds-abc123.json",  # google-github-actions credential file
]

# Files the guard MUST allow (templates, public keys, ordinary source).
ALLOW_FILE = [
    ".env.example",
    ".env.sample",
    "id_rsa.pub",
    "id_ed25519.pub",
    "config.json",
    "package.json",
    "src/main.py",
    "README.md",
]


@pytest.mark.parametrize("path", BLOCK_FILE)
def test_sensitive_guard_blocks(path: str) -> None:
    assert _run_file(path) == 2, f"sensitive-file guard should BLOCK: {path!r}"


@pytest.mark.parametrize("path", ALLOW_FILE)
def test_sensitive_guard_allows(path: str) -> None:
    assert _run_file(path) == 0, f"sensitive-file guard should ALLOW: {path!r}"
