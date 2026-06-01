"""Tests for the `dotfiles doctor` Typer command."""

from pathlib import Path

from typer.testing import CliRunner

from dotfiles.cli.main import app
from tests.fakes import make_fake_context

runner = CliRunner()


def test_doctor_runs_and_groups(monkeypatch) -> None:
    """Bare fake context → missing tools → exit 1, section headers printed."""
    ctx = make_fake_context()  # bare machine: nothing installed
    result = runner.invoke(app, ["doctor"], obj=ctx)
    assert result.exit_code == 1
    assert "Core Tools" in result.output


def test_doctor_help_has_fix_flag() -> None:
    result = runner.invoke(app, ["doctor", "--help"])
    assert result.exit_code == 0
    assert "--fix" in result.output


def test_doctor_fix_prints_agent_setup_hint() -> None:
    """--fix output must contain the agent-setup hint."""
    ctx = make_fake_context()
    result = runner.invoke(app, ["doctor", "--fix"], obj=ctx)
    assert "dotfiles agent setup" in result.output


def test_doctor_all_ok_exits_zero() -> None:
    """When all checks pass, exit code is 0."""
    from datetime import UTC, datetime

    from dotfiles.cli.context import AppContext
    from dotfiles.core.settings import Settings
    from tests.fakes import (
        FakeClock,
        FakeFileSystem,
        FakeProcessRunner,
        FakeSessionLauncher,
    )

    _all_tools = {
        "brew",
        "git",
        "jq",
        "yq",
        "cursor",
        "zed",
        "bun",
        "fnm",
        "uv",
        "go",
        "node",
        "npx",
        "python3.14",
        "claude",
        "gh",
        "just",
        "delta",
        "golangci-lint",
        "mosh",
        "zellij",
        "codex",
        "tailscale",
    }

    def _which(name: str) -> str | None:
        return f"/usr/bin/{name}" if name in _all_tools else None

    runner_fake = FakeProcessRunner()
    home = Path("/home/evan")
    runner_fake.script(("fnm", "list"), stdout="v20.0.0\n")
    runner_fake.script(("node", "--version"), stdout="v20.0.0\n")
    runner_fake.script(("python3.14", "--version"), stdout="Python 3.14.0\n")
    runner_fake.script(("gh", "extension", "list"), stdout="shuymn/gh-mcp\n")
    runner_fake.script(
        ("jq", ".enabledPlugins // {} | length", str(home / ".claude" / "settings.json")),
        stdout="1\n",
    )
    runner_fake.script(
        ("jq", ".hooks // {} | keys | length", str(home / ".claude" / "settings.json")),
        stdout="1\n",
    )
    runner_fake.script(
        ("jq", ".mcpServers // {} | length", str(home / ".claude.json")),
        stdout="1\n",
    )

    fs = FakeFileSystem()
    dotfiles = Path("/home/evan/dotfiles")
    fs.mkdir(Path("/Applications/Termius.app"))
    fs.symlink(dotfiles / "shell" / ".zshrc", home / ".zshrc")
    fs.symlink(dotfiles / "git" / ".gitconfig", home / ".gitconfig")
    fs.symlink(dotfiles / "shell" / ".zprofile", home / ".zprofile")
    fs.symlink(Path("/usr/bin/node"), Path("/opt/homebrew/bin/node"))
    fs.write_text(home / ".gitconfig.local", "[user]\n  email = test@test.com\n")
    fs.write_text(home / ".claude" / "CLAUDE.md", "# Claude\n")
    fs.write_text(
        home / ".claude" / "settings.json",
        '{"enabledPlugins": {"x": 1}, "hooks": {"a": []}}\n',
    )
    fs.write_text(home / ".claude.json", '{"mcpServers": {"x": {}}}\n')
    fs.write_text(home / ".codex" / "AGENTS.md", "# Codex\n")
    fs.write_text(home / ".codex" / "hooks.json", "{}\n")
    fs.write_text(home / ".codex" / "config.toml", "[mcp_servers]\n")
    fs.write_text(home / ".config" / "ghostty" / "config", "font-size = 14\n")

    ctx = AppContext(
        runner=runner_fake,
        fs=fs,
        clock=FakeClock(datetime(2026, 5, 31, tzinfo=UTC)),
        settings=Settings(),
        interactive=False,
        home=home,
        launcher=FakeSessionLauncher(),
        dotfiles_dir=dotfiles,
    )

    cli_runner = CliRunner()
    result = cli_runner.invoke(app, ["doctor"], obj=ctx)
    assert result.exit_code == 0, f"Unexpected failures:\n{result.output}"
