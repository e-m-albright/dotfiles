"""Tests for Hide My Email behavior."""

from __future__ import annotations

import pytest

from dotfiles.cmd.email.icloud import parse_icloud_mask
from dotfiles.cmd.email.service import (
    MaskError,
    create_mask,
    deactivate_mask,
    delete_mask,
    find_mask,
    list_masks,
)
from dotfiles.cmd.email.service import copy_to_clipboard as copy
from dotfiles.testing.fakes import FakeMaskProvider, FakeProcessRunner

_RECORDS = [
    {"hme": "a@icloud.com", "label": "Shopping", "anonymousId": "id-a", "isActive": True},
    {"hme": "b@icloud.com", "label": "Spam", "anonymousId": "id-b", "isActive": False},
]

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


def test_provider_exception_becomes_mask_error() -> None:
    class BrokenProvider(FakeMaskProvider):
        def generate(self) -> str | None:
            raise RuntimeError("network down")

    with pytest.raises(MaskError, match="network down"):
        create_mask(BrokenProvider(), "x")


def test_mutations_reject_explicit_provider_failure() -> None:
    class RejectingProvider(FakeMaskProvider):
        def deactivate(self, anonymous_id: str) -> dict[str, object]:
            return {"success": False, "error": "rejected"}

        def delete(self, anonymous_id: str) -> dict[str, object]:
            raise RuntimeError("offline")

    provider = RejectingProvider()
    with pytest.raises(MaskError, match="rejected"):
        deactivate_mask(provider, "id")
    with pytest.raises(MaskError, match="offline"):
        delete_mask(provider, "id")


# ---------------------------------------------------------------------------
# list_masks
# ---------------------------------------------------------------------------


def test_list_masks_parses_records_in_order() -> None:
    masks = list_masks(FakeMaskProvider(existing=_RECORDS))
    assert [m.address for m in masks] == ["a@icloud.com", "b@icloud.com"]
    assert masks[0].label == "Shopping"
    assert masks[0].anonymous_id == "id-a"
    assert masks[0].active is True
    assert masks[1].active is False


def test_list_masks_tolerates_missing_keys() -> None:
    # iCloud occasionally omits label/note; parsing must not blow up and defaults active.
    [mask] = list_masks(FakeMaskProvider(existing=[{"hme": "x@icloud.com", "anonymousId": "id-x"}]))
    assert mask.address == "x@icloud.com"
    assert mask.label == ""
    assert mask.active is True


@pytest.mark.parametrize(
    "record",
    [
        {"anonymousId": "id-x"},
        {"hme": "x@icloud.com"},
        {"hme": "x@icloud.com", "anonymousId": "id-x", "isActive": "false"},
    ],
)
def test_list_masks_rejects_unusable_provider_records(record: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="alias"):
        parse_icloud_mask(record)


def test_list_masks_empty() -> None:
    assert list_masks(FakeMaskProvider(existing=[])) == []


# ---------------------------------------------------------------------------
# find_mask
# ---------------------------------------------------------------------------


def test_find_mask_by_address_and_by_id() -> None:
    masks = list_masks(FakeMaskProvider(existing=_RECORDS))
    assert find_mask(masks, "a@icloud.com").anonymous_id == "id-a"
    assert find_mask(masks, "id-b").address == "b@icloud.com"


def test_find_mask_missing_raises() -> None:
    masks = list_masks(FakeMaskProvider(existing=_RECORDS))
    with pytest.raises(MaskError, match="No Hide My Email alias matching"):
        find_mask(masks, "nope@icloud.com")


def test_find_mask_ambiguous_raises() -> None:
    dupes = [
        {"hme": "dup@icloud.com", "anonymousId": "id-1"},
        {"hme": "dup@icloud.com", "anonymousId": "id-2"},
    ]
    masks = list_masks(FakeMaskProvider(existing=dupes))
    with pytest.raises(MaskError, match="matches several aliases"):
        find_mask(masks, "dup@icloud.com")


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


def test_copy_to_clipboard_reports_execution_failure() -> None:
    runner = FakeProcessRunner()
    runner.script(("pbcopy",), exit_code=1)
    assert copy(runner, "a@icloud.com", which=lambda _name: "/usr/bin/pbcopy") is False
