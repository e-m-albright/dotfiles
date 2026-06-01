"""Tests for DoctorService core logic."""

from pathlib import Path

from dotfiles.core.doctor import DoctorService
from dotfiles.core.models import CheckResult
from tests.fakes import FakeFileSystem, FakeProcessRunner


def _svc(runner=None, fs=None, *, fix=False, which=None):
    return DoctorService(
        runner=runner or FakeProcessRunner(),
        fs=fs or FakeFileSystem(),
        home=Path("/home/evan"),
        dotfiles_dir=Path("/home/evan/dotfiles"),
        fix=fix,
        which=which or (lambda _name: None),
    )


def test_check_result_fields() -> None:
    c = CheckResult(section="Core Tools", name="Git", status="ok", detail="git 2.4", hint="")
    assert c.status == "ok"
    assert c.is_failure is False
    assert (
        CheckResult(section="x", name="y", status="missing", hint="brew install y").is_failure
        is True
    )
    assert CheckResult(section="x", name="y", status="warn").is_failure is False


def test_tool_present_and_absent() -> None:
    runner = FakeProcessRunner()
    runner.script(("git", "--version"), stdout="git version 2.43\n")
    svc = _svc(runner, which=lambda n: "/usr/bin/git" if n == "git" else None)
    ok = svc._tool("Core Tools", "Git", "git", "brew install git")
    assert ok.status == "ok"
    assert "2.43" in ok.detail
    missing = svc._tool("Core Tools", "Nope", "nope-bin", "install nope")
    assert missing.status == "missing"
    assert missing.hint == "install nope"


def test_app_bundle_check() -> None:
    fs = FakeFileSystem()
    fs.mkdir(Path("/Applications/Termius.app"))
    svc = _svc(fs=fs)
    present = svc._app(
        "Remote Shell", "Termius", Path("/Applications/Termius.app"), "brew install --cask termius"
    )
    assert present.status == "ok"
    absent = svc._app("Editors", "Ghost", Path("/Applications/Ghost.app"), "hint")
    assert absent.status == "missing"


def test_symlink_check_and_fix() -> None:
    src = Path("/home/evan/dotfiles/shell/.zshrc")
    dest = Path("/home/evan/.zshrc")
    fs = FakeFileSystem()
    # not linked -> missing without fix
    assert _svc(fs=fs)._symlink("Configuration", ".zshrc", src, dest).status == "missing"
    # with fix -> creates link, status fixed
    fs2 = FakeFileSystem()
    res = _svc(fs=fs2, fix=True)._symlink("Configuration", ".zshrc", src, dest)
    assert res.status == "fixed"
    assert fs2.is_symlink(dest)
    # already linked -> ok
    fs3 = FakeFileSystem()
    fs3.symlink(src, dest)
    assert _svc(fs=fs3)._symlink("Configuration", ".zshrc", src, dest).status == "ok"


# ---------------------------------------------------------------------------
# Task 4: run() — full check list
# ---------------------------------------------------------------------------

_ALL_TOOLS = {
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


def _fully_equipped_which(name: str) -> str | None:
    return f"/usr/bin/{name}" if name in _ALL_TOOLS else None


def _fully_equipped_runner() -> FakeProcessRunner:
    runner = FakeProcessRunner()
    # fnm list — contains a version so Node.js check is ok
    runner.script(("fnm", "list"), stdout="v20.0.0\n")
    runner.script(("node", "--version"), stdout="v20.0.0\n")
    # python3.14 version
    runner.script(("python3.14", "--version"), stdout="Python 3.14.0\n")
    # gh extension list — contains gh-mcp
    runner.script(("gh", "extension", "list"), stdout="shuymn/gh-mcp\n")
    # jq counts: plugins=1, hooks=1, mcp=1
    home = Path("/home/evan")
    runner.script(
        ("jq", ".enabledPlugins // {} | length", str(home / ".claude" / "settings.json")),
        stdout="1\n",
    )
    runner.script(
        ("jq", ".hooks // {} | keys | length", str(home / ".claude" / "settings.json")),
        stdout="1\n",
    )
    runner.script(
        ("jq", ".mcpServers // {} | length", str(home / ".claude.json")),
        stdout="1\n",
    )
    return runner


def _fully_equipped_fs() -> FakeFileSystem:
    fs = FakeFileSystem()
    home = Path("/home/evan")
    dotfiles = Path("/home/evan/dotfiles")

    # App bundles
    fs.mkdir(Path("/Applications/Termius.app"))

    # Symlinks
    fs.symlink(dotfiles / "shell" / ".zshrc", home / ".zshrc")
    fs.symlink(dotfiles / "git" / ".gitconfig", home / ".gitconfig")
    fs.symlink(dotfiles / "shell" / ".zprofile", home / ".zprofile")
    node_link = Path("/opt/homebrew/bin/node")
    fs.symlink(Path("/usr/bin/node"), node_link)

    # Config files
    fs.write_text(home / ".gitconfig.local", "[user]\n  email = test@test.com\n")
    fs.write_text(home / ".claude" / "CLAUDE.md", "# Claude\n")
    fs.write_text(
        home / ".claude" / "settings.json", '{"enabledPlugins": {"x": 1}, "hooks": {"a": []}}\n'
    )
    fs.write_text(home / ".claude.json", '{"mcpServers": {"x": {}}}\n')
    fs.write_text(home / ".codex" / "AGENTS.md", "# Codex\n")
    fs.write_text(home / ".codex" / "hooks.json", "{}\n")
    fs.write_text(home / ".codex" / "config.toml", "[mcp_servers]\n")
    fs.write_text(home / ".config" / "ghostty" / "config", "font-size = 14\n")

    return fs


def test_run_groups_sections_and_overall_failure() -> None:
    svc = _svc()  # bare: nothing installed, no tools on which
    results = svc.run()
    sections = [r.section for r in results]
    assert "Core Tools" in sections
    assert "Remote Shell" in sections
    assert any(r.is_failure for r in results)  # bare machine fails


def test_run_all_present_has_no_failure() -> None:
    svc = DoctorService(
        runner=_fully_equipped_runner(),
        fs=_fully_equipped_fs(),
        home=Path("/home/evan"),
        dotfiles_dir=Path("/home/evan/dotfiles"),
        fix=False,
        which=_fully_equipped_which,
    )
    results = svc.run()
    failures = [r for r in results if r.is_failure]
    assert not failures, f"Unexpected failures: {[(r.name, r.hint) for r in failures]}"
