"""Tests for the `dotfiles email-mask` Typer command."""

from __future__ import annotations

from typer.testing import CliRunner

from dotfiles.app.main import app
from dotfiles.cmd.email.service import copy_to_clipboard
from dotfiles.settings import Settings
from dotfiles.testing.fakes import FakeMaskProvider, FakeProcessRunner, make_fake_context

runner = CliRunner()

_ME = "me@icloud.com"
_RECORDS = [
    {"hme": "a@icloud.com", "label": "Shopping", "anonymousId": "id-a", "isActive": True},
    {"hme": "b@icloud.com", "label": "Spam", "anonymousId": "id-b", "isActive": False},
]


def _ctx_with(provider: FakeMaskProvider, *, account: str = _ME) -> object:
    return make_fake_context(mask_provider=provider, settings=Settings(apple_id=account))


def test_email_help_lists_all_commands() -> None:
    result = runner.invoke(app, ["email-mask", "--help"])
    assert result.exit_code == 0
    for cmd in ("create", "list", "delete", "deactivate"):
        assert cmd in result.output


def test_mask_generates_reserves_and_copies(monkeypatch) -> None:
    provider = FakeMaskProvider(address="new@icloud.com")
    proc = FakeProcessRunner()
    monkeypatch.setattr(
        "dotfiles.cmd.email.cli.copy_to_clipboard",
        lambda process, text: copy_to_clipboard(
            process, text, which=lambda _name: "/usr/bin/pbcopy"
        ),
    )
    ctx = make_fake_context(
        runner=proc,
        mask_provider=provider,
        settings=Settings(apple_id="me@icloud.com"),
    )
    result = runner.invoke(app, ["email-mask", "create", "Shopping"], obj=ctx)
    assert result.exit_code == 0
    assert "new@icloud.com" in result.output
    assert provider.reserved == [("new@icloud.com", "Shopping")]
    assert proc.calls == [("pbcopy",)]  # copied by default
    assert proc.inputs == ["new@icloud.com"]


def test_mask_no_copy_skips_clipboard() -> None:
    proc = FakeProcessRunner()
    ctx = make_fake_context(
        runner=proc,
        mask_provider=FakeMaskProvider(),
        settings=Settings(apple_id="me@icloud.com"),
    )
    result = runner.invoke(app, ["email-mask", "create", "--no-copy"], obj=ctx)
    assert result.exit_code == 0
    assert ("pbcopy",) not in proc.calls


def test_mask_uses_default_label_when_omitted() -> None:
    provider = FakeMaskProvider()
    ctx = make_fake_context(mask_provider=provider, settings=Settings(apple_id="me@icloud.com"))
    result = runner.invoke(app, ["email-mask", "create"], obj=ctx)
    assert result.exit_code == 0
    assert provider.reserved[0][1] == "dotfiles"


def test_bare_email_mask_creates_and_copies() -> None:
    provider = FakeMaskProvider()
    ctx = make_fake_context(mask_provider=provider, settings=Settings(apple_id="me@icloud.com"))
    result = runner.invoke(app, ["email-mask"], obj=ctx)
    assert result.exit_code == 0
    assert provider.reserved[0][1] == "dotfiles"


def test_mask_errors_without_account() -> None:
    ctx = make_fake_context(settings=Settings(apple_id=""))
    result = runner.invoke(app, ["email-mask", "create"], obj=ctx)
    assert result.exit_code == 1
    assert "No iCloud account" in result.output


def test_mask_reports_generation_failure() -> None:
    # generate() returning None surfaces as a clean error + exit 1, not a traceback.
    ctx = make_fake_context(
        mask_provider=FakeMaskProvider(address=None),
        settings=Settings(apple_id="me@icloud.com"),
    )
    result = runner.invoke(app, ["email-mask", "create"], obj=ctx)
    assert result.exit_code == 1
    assert "declined to generate" in result.output


# ---------------------------------------------------------------------------
# list / deactivate / delete
# ---------------------------------------------------------------------------


def test_list_renders_addresses_and_inactive_marker() -> None:
    ctx = _ctx_with(FakeMaskProvider(existing=_RECORDS))
    result = runner.invoke(app, ["email-mask", "list"], obj=ctx)
    assert result.exit_code == 0
    assert "a@icloud.com" in result.output
    assert "b@icloud.com" in result.output
    assert "inactive" in result.output  # the deactivated alias is flagged


def test_list_empty_is_friendly() -> None:
    ctx = _ctx_with(FakeMaskProvider(existing=[]))
    result = runner.invoke(app, ["email-mask", "list"], obj=ctx)
    assert result.exit_code == 0
    assert "No aliases yet" in result.output


def test_deactivate_calls_provider_with_resolved_id() -> None:
    provider = FakeMaskProvider(existing=_RECORDS)
    result = runner.invoke(
        app, ["email-mask", "deactivate", "a@icloud.com"], obj=_ctx_with(provider)
    )
    assert result.exit_code == 0
    assert provider.deactivated == ["id-a"]


def test_delete_is_dry_run_by_default() -> None:
    provider = FakeMaskProvider(existing=_RECORDS)
    result = runner.invoke(app, ["email-mask", "delete", "a@icloud.com"], obj=_ctx_with(provider))
    assert result.exit_code == 0
    assert "Would delete" in result.output
    assert provider.deleted == []  # nothing removed without --yes


def test_delete_with_yes_commits() -> None:
    provider = FakeMaskProvider(existing=_RECORDS)
    result = runner.invoke(app, ["email-mask", "delete", "id-b", "--yes"], obj=_ctx_with(provider))
    assert result.exit_code == 0
    assert provider.deleted == ["id-b"]


def test_delete_unknown_selector_errors() -> None:
    provider = FakeMaskProvider(existing=_RECORDS)
    result = runner.invoke(
        app, ["email-mask", "delete", "ghost@icloud.com"], obj=_ctx_with(provider)
    )
    assert result.exit_code == 1
    assert "No Hide My Email alias" in result.output
    assert provider.deleted == []
