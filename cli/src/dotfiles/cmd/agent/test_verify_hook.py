"""Behavioral tests for the verify-before-done Stop hook (kernel K1).

``ai/agents/shared/hooks/verify-before-done.sh`` blocks a turn that *claims*
something passes/works/is verified while running zero tools to check it. These
tests feed it synthetic Claude-Code transcripts and assert the decision:
a ``"block"`` on stdout = nudge, empty stdout = allow. The vectors are the
contract — the hook must stay conservative (no false blocks).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[5]
_HOOK = _REPO / "ai" / "agents" / "shared" / "hooks" / "verify-before-done.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("jq") is None,
    reason="verify hook needs bash + jq",
)


def _human(text: str) -> dict[str, object]:
    return {"type": "user", "message": {"role": "user", "content": text}}


def _assistant_text(text: str) -> dict[str, object]:
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def _assistant_tool() -> dict[str, object]:
    return {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [{"type": "tool_use", "name": "Bash", "id": "t1", "input": {}}],
        },
    }


def _tool_result() -> dict[str, object]:
    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}],
        },
    }


def _run(tmp_path: Path, events: list[dict[str, object]], *, stop_active: bool = False) -> str:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    payload = json.dumps({"transcript_path": str(transcript), "stop_hook_active": stop_active})
    result = subprocess.run(
        ["bash", str(_HOOK)], input=payload, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"hook must always exit 0; stderr={result.stderr!r}"
    return result.stdout.strip()


def _blocked(stdout: str) -> bool:
    return bool(stdout) and json.loads(stdout).get("decision") == "block"


def test_claim_without_tools_is_blocked(tmp_path: Path) -> None:
    out = _run(tmp_path, [_human("fix the bug"), _assistant_text("Done — all tests pass.")])
    assert _blocked(out)


def test_claim_with_a_tool_this_turn_is_allowed(tmp_path: Path) -> None:
    out = _run(
        tmp_path,
        [_human("fix it"), _assistant_tool(), _tool_result(), _assistant_text("All tests pass.")],
    )
    assert not _blocked(out)


def test_no_claim_is_allowed(tmp_path: Path) -> None:
    out = _run(tmp_path, [_human("fix it"), _assistant_text("I updated the file and moved on.")])
    assert not _blocked(out)


def test_prior_turn_tools_do_not_count(tmp_path: Path) -> None:
    # The tool ran BEFORE the last human message; the claim is in a fresh turn
    # with no verification → still a block.
    out = _run(
        tmp_path,
        [
            _human("run tests"),
            _assistant_tool(),
            _tool_result(),
            _human("now ship it"),
            _assistant_text("Shipped — the build passes."),
        ],
    )
    assert _blocked(out)


def test_stop_hook_active_never_blocks(tmp_path: Path) -> None:
    # Already re-prompted once → must not nudge again (loop guard).
    out = _run(
        tmp_path,
        [_human("fix"), _assistant_text("all tests pass")],
        stop_active=True,
    )
    assert not _blocked(out)


# Innocent final messages that an earlier, unanchored pattern set wrongly blocked
# (the "test" inside "latest", "it works" inside "commit works", a question, and a
# report of prior CI state). The hook must ALLOW all of these.
_FALSE_POSITIVES = [
    "The latest passing run was yesterday, so we're good.",
    "commit works fine on my side",
    "Want me to confirm it works?",
    "tests pass locally per CI history, but I haven't run them here.",
]


@pytest.mark.parametrize("text", _FALSE_POSITIVES)
def test_innocent_phrasings_are_not_blocked(tmp_path: Path, text: str) -> None:
    out = _run(tmp_path, [_human("status?"), _assistant_text(text)])
    assert not _blocked(out), f"false block on innocent text: {text!r}"


def test_missing_transcript_fails_open(tmp_path: Path) -> None:
    payload = json.dumps(
        {"transcript_path": str(tmp_path / "nope.jsonl"), "stop_hook_active": False}
    )
    result = subprocess.run(
        ["bash", str(_HOOK)], input=payload, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""
