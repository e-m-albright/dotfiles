"""Tests for the `dotfiles password` command and its generator."""

from __future__ import annotations

import string

from typer.testing import CliRunner

from dotfiles.app.main import app
from dotfiles.cmd.email.service import copy_to_clipboard
from dotfiles.cmd.password.service import generate_password
from dotfiles.testing.fakes import FakeProcessRunner, make_fake_context

runner = CliRunner()

_ALPHANUMERIC = set(string.ascii_letters + string.digits)


def test_generate_password_default_is_20_alphanumeric_chars() -> None:
    password = generate_password()
    assert len(password) == 20
    assert set(password) <= _ALPHANUMERIC


def test_generate_password_respects_length() -> None:
    for length in (8, 20, 64):
        assert len(generate_password(length)) == length


def test_generate_password_contains_every_character_class() -> None:
    for _ in range(50):
        password = generate_password(8)
        assert set(password) & set(string.ascii_lowercase)
        assert set(password) & set(string.ascii_uppercase)
        assert set(password) & set(string.digits)


def test_generate_password_is_not_deterministic() -> None:
    assert generate_password() != generate_password()


def test_password_prints_and_copies_by_default(monkeypatch) -> None:
    proc = FakeProcessRunner()
    monkeypatch.setattr(
        "dotfiles.cmd.password.cli.copy_to_clipboard",
        lambda process, text: copy_to_clipboard(
            process, text, which=lambda _name: "/usr/bin/pbcopy"
        ),
    )
    result = runner.invoke(app, ["password"], obj=make_fake_context(runner=proc))
    assert result.exit_code == 0
    assert proc.calls == [("pbcopy",)]
    assert len(proc.inputs) == 1
    copied = proc.inputs[0]
    assert len(copied) == 20
    assert copied in result.output  # printed as well as copied


def test_password_custom_length() -> None:
    proc = FakeProcessRunner()
    result = runner.invoke(app, ["password", "32", "--no-copy"], obj=make_fake_context(runner=proc))
    assert result.exit_code == 0
    printed = [
        word
        for line in result.output.splitlines()
        for word in line.split()
        if set(word) <= _ALPHANUMERIC and len(word) == 32
    ]
    assert printed, result.output


def test_password_no_copy_skips_clipboard() -> None:
    proc = FakeProcessRunner()
    result = runner.invoke(app, ["password", "--no-copy"], obj=make_fake_context(runner=proc))
    assert result.exit_code == 0
    assert ("pbcopy",) not in proc.calls


def test_password_rejects_nonpositive_length() -> None:
    result = runner.invoke(app, ["password", "0"], obj=make_fake_context())
    assert result.exit_code != 0
