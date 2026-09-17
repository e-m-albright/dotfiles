"""Editor integration must not advertise the retired restricted agent route."""

from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]


def test_zed_has_no_lima_agent_bridge() -> None:
    settings = (_REPO / "editors/zed/settings.json").read_text()
    assert '"codex-lima"' not in settings
    assert "workbench lima" not in settings
    assert "host authority" in settings


def test_ghostty_does_not_grant_automatic_clipboard_access() -> None:
    settings = (_REPO / "terminal/ghostty.config").read_text()
    values = dict(
        line.split("=", 1)
        for line in settings.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    )
    values = {key.strip(): value.strip() for key, value in values.items()}
    assert values["clipboard-read"] == "deny"
    assert values["clipboard-write"] == "ask"
