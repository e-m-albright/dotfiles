"""Native options remain discoverable and route without invoking host mutations."""

import pytest
from typer.testing import CliRunner

from dotfiles.app import main
from dotfiles.testing.fakes import make_fake_context


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["install", "--plan", "--profile", "work"], ("install", ["--plan", "--profile", "work"])),
        (["update", "--profile", "personal"], ("update", ["--profile", "personal"])),
    ],
)
def test_native_profile_options_reach_shim(monkeypatch, args, expected):
    calls = []
    monkeypatch.setattr(
        main, "_delegate_to_shim", lambda name, options: calls.append((name, options))
    )
    result = CliRunner().invoke(main.app, args, obj=make_fake_context())
    assert result.exit_code == 0, result.output
    assert calls == [expected]
