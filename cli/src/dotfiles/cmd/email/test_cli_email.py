"""Tests for the `dotfiles email mask` Typer command."""

from __future__ import annotations

from typer.testing import CliRunner

from dotfiles.app.main import app
from dotfiles.settings import Settings
from dotfiles.testing.fakes import FakeMaskProvider, FakeProcessRunner, make_fake_context

runner = CliRunner()


def test_email_help_lists_mask() -> None:
    result = runner.invoke(app, ["email", "--help"])
    assert result.exit_code == 0
    assert "mask" in result.output


def test_mask_generates_reserves_and_copies() -> None:
    provider = FakeMaskProvider(address="new@icloud.com")
    proc = FakeProcessRunner()
    ctx = make_fake_context(
        runner=proc,
        mask_provider=provider,
        settings=Settings(apple_id="me@icloud.com"),
    )
    result = runner.invoke(app, ["email", "mask", "Shopping"], obj=ctx)
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
    result = runner.invoke(app, ["email", "mask", "--no-copy"], obj=ctx)
    assert result.exit_code == 0
    assert ("pbcopy",) not in proc.calls


def test_mask_uses_default_label_when_omitted() -> None:
    provider = FakeMaskProvider()
    ctx = make_fake_context(mask_provider=provider, settings=Settings(apple_id="me@icloud.com"))
    result = runner.invoke(app, ["email", "mask"], obj=ctx)
    assert result.exit_code == 0
    assert provider.reserved[0][1] == "dotfiles"


def test_mask_errors_without_account() -> None:
    ctx = make_fake_context(settings=Settings(apple_id=""))
    result = runner.invoke(app, ["email", "mask"], obj=ctx)
    assert result.exit_code == 1
    assert "No iCloud account" in result.output


def test_mask_reports_generation_failure() -> None:
    # generate() returning None surfaces as a clean error + exit 1, not a traceback.
    ctx = make_fake_context(
        mask_provider=FakeMaskProvider(address=None),
        settings=Settings(apple_id="me@icloud.com"),
    )
    result = runner.invoke(app, ["email", "mask"], obj=ctx)
    assert result.exit_code == 1
    assert "declined to generate" in result.output
