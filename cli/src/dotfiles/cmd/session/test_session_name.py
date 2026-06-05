"""Tests for the session-name rule — the one place that owns what's allowed."""

from dotfiles.cmd.session import session_name


def test_is_valid_accepts_ordinary_names() -> None:
    assert session_name.is_valid("api")
    assert session_name.is_valid("api-server_2")


def test_is_valid_rejects_empty_and_whitespace() -> None:
    assert not session_name.is_valid("")
    assert not session_name.is_valid("two words")
    assert not session_name.is_valid("  ")


def test_error_explains_spaces_but_is_silent_on_empty() -> None:
    # An empty field has nothing to complain about yet — only characters do.
    assert session_name.error("") is None
    assert session_name.error("api") is None
    assert session_name.error("two words") == "Session name cannot contain spaces"


def test_clean_drops_invalid_characters() -> None:
    assert session_name.clean("two words") == "twowords"
    assert session_name.clean("  a b  ") == "ab"
    assert session_name.clean("api") == "api"


def test_clean_output_is_always_error_free() -> None:
    # Whatever the rule forbids, clean() must produce something error() accepts.
    assert session_name.error(session_name.clean("a \t b\n")) is None
