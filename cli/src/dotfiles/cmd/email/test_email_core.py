"""Tests for the Hide My Email core: create_mask + copy_to_clipboard."""

from __future__ import annotations

import pytest

from dotfiles.cmd.email.service import MaskError, create_mask
from dotfiles.cmd.email.service import copy_to_clipboard as copy
from dotfiles.testing.fakes import FakeMaskProvider, FakeProcessRunner

# ---------------------------------------------------------------------------
# create_mask
# ---------------------------------------------------------------------------


def test_create_mask_generates_then_reserves_under_label() -> None:
    provider = FakeMaskProvider(address="zzz@icloud.com", anonymous_id="anon-9")
    reserved = create_mask(provider, "Newsletters")
    assert provider.generated == 1
    assert provider.reserved == [("zzz@icloud.com", "Newsletters")]
    assert reserved.address == "zzz@icloud.com"
    assert reserved.label == "Newsletters"
    assert reserved.anonymous_id == "anon-9"


def test_create_mask_prefers_reserve_echoed_address() -> None:
    # reserve() echoes the canonical `hme`; create_mask trusts it over the generated value.
    provider = FakeMaskProvider(address="canonical@icloud.com")
    assert create_mask(provider, "x").address == "canonical@icloud.com"


def test_create_mask_tolerates_missing_anonymous_id() -> None:
    provider = FakeMaskProvider(address="a@icloud.com", anonymous_id=None)
    assert create_mask(provider, "x").anonymous_id is None


def test_create_mask_raises_when_generate_returns_none() -> None:
    provider = FakeMaskProvider(address=None)
    with pytest.raises(MaskError, match="declined to generate"):
        create_mask(provider, "x")
    assert provider.reserved == []  # never attempts to reserve a non-existent address


# ---------------------------------------------------------------------------
# copy_to_clipboard
# ---------------------------------------------------------------------------


def test_copy_to_clipboard_pipes_text_to_pbcopy() -> None:
    runner = FakeProcessRunner()
    assert copy(runner, "a@icloud.com", which=lambda _name: "/usr/bin/pbcopy") is True
    assert runner.calls == [("pbcopy",)]
    assert runner.inputs == ["a@icloud.com"]


def test_copy_to_clipboard_no_op_without_pbcopy() -> None:
    runner = FakeProcessRunner()
    assert copy(runner, "a@icloud.com", which=lambda _name: None) is False
    assert runner.calls == []  # nothing run off macOS
