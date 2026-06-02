"""Tests for DoctorService core logic."""

from pathlib import Path

from dotfiles.cmd.doctor.models import CheckResult
from dotfiles.cmd.doctor.service import DoctorService
from dotfiles.testing.fakes import FakeProcessRunner, write_tree


def _svc(runner=None, *, fix=False, which=None, home=None, dotfiles_dir=None):
    return DoctorService(
        runner=runner or FakeProcessRunner(),
        home=home or Path("/nonexistent/home"),
        dotfiles_dir=dotfiles_dir or Path("/nonexistent/dotfiles"),
        fix=fix,
        which=which or (lambda _name: None),
        # Point system-path checks at nonexistent dirs so tests never depend on
        # the host's real /Applications or /opt/homebrew.
        apps_dir=Path("/nonexistent/Applications"),
        brew_bin=Path("/nonexistent/brew-bin"),
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


def test_app_bundle_check(tmp_path: Path) -> None:
    app_path = tmp_path / "Termius.app"
    app_path.mkdir()
    svc = _svc()
    present = svc._app("Remote Shell", "Termius", app_path, "brew install --cask termius")
    assert present.status == "ok"
    absent = svc._app("Editors", "Ghost", tmp_path / "Ghost.app", "hint")
    assert absent.status == "missing"


def test_symlink_check_and_fix(tmp_path: Path) -> None:
    src = tmp_path / "dotfiles" / "shell" / ".zshrc"
    dest = tmp_path / "home" / ".zshrc"
    src.parent.mkdir(parents=True)
    src.write_text("# zshrc")

    # not linked -> missing without fix
    assert (
        _svc(home=tmp_path / "home")._symlink("Configuration", ".zshrc", src, dest).status
        == "missing"
    )

    # with fix -> creates link, status fixed
    (tmp_path / "home").mkdir(parents=True, exist_ok=True)
    res = _svc(home=tmp_path / "home", fix=True)._symlink("Configuration", ".zshrc", src, dest)
    assert res.status == "fixed"
    assert dest.is_symlink()

    # already linked -> ok
    assert (
        _svc(home=tmp_path / "home")._symlink("Configuration", ".zshrc", src, dest).status == "ok"
    )


# ---------------------------------------------------------------------------
# run() — full check list
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


def _fully_equipped_runner(home: Path) -> FakeProcessRunner:
    runner = FakeProcessRunner()
    # fnm list — contains a version so Node.js check is ok
    runner.script(("fnm", "list"), stdout="v20.0.0\n")
    runner.script(("node", "--version"), stdout="v20.0.0\n")
    # python3.14 version
    runner.script(("python3.14", "--version"), stdout="Python 3.14.0\n")
    # gh extension list — contains gh-mcp
    runner.script(("gh", "extension", "list"), stdout="shuymn/gh-mcp\n")
    # jq counts: plugins=1, hooks=1, mcp=1
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


def test_run_groups_sections_and_overall_failure() -> None:
    svc = _svc()  # bare: nothing installed, no tools on which
    results = svc.run()
    sections = [r.section for r in results]
    assert "Core Tools" in sections
    assert "Remote Shell" in sections
    assert any(r.is_failure for r in results)  # bare machine fails


def test_run_all_present_has_no_failure(tmp_path: Path) -> None:
    home = tmp_path / "home"
    dotfiles = tmp_path / "dotfiles"

    runner = _fully_equipped_runner(home)

    # Symlink sources (must exist so readlink + str-contains works)
    shell_dir = dotfiles / "shell"
    git_dir = dotfiles / "git"
    shell_dir.mkdir(parents=True)
    git_dir.mkdir(parents=True)
    (shell_dir / ".zshrc").write_text("# zshrc")
    (shell_dir / ".zprofile").write_text("# zprofile")
    (git_dir / ".gitconfig").write_text("[core]\n")

    home.mkdir(parents=True)
    (home / ".zshrc").symlink_to(shell_dir / ".zshrc")
    (home / ".gitconfig").symlink_to(git_dir / ".gitconfig")
    (home / ".zprofile").symlink_to(shell_dir / ".zprofile")

    # System-path checks resolved under tmp_path (injected), so no host dependence.
    apps_dir = tmp_path / "Applications"
    apps_dir.mkdir()
    (apps_dir / "Termius.app").mkdir()  # _app() only checks the bundle exists
    brew_bin = tmp_path / "brew-bin"
    brew_bin.mkdir()
    real_node = tmp_path / "node-real"
    real_node.write_text("#!/bin/sh\n")
    (brew_bin / "node").symlink_to(real_node)  # GUI-app node symlink present

    write_tree(
        home,
        {
            ".gitconfig.local": "[user]\n  email = test@test.com\n",
            ".claude/CLAUDE.md": "# Claude\n",
            ".claude/settings.json": '{"enabledPlugins": {"x": 1}, "hooks": {"a": []}}\n',
            ".claude.json": '{"mcpServers": {"x": {}}}\n',
            ".codex/AGENTS.md": "# Codex\n",
            ".codex/hooks.json": "{}\n",
            ".codex/config.toml": "[mcp_servers]\n",
            ".config/ghostty/config": "font-size = 14\n",
        },
    )

    svc = DoctorService(
        runner=runner,
        home=home,
        dotfiles_dir=dotfiles,
        fix=False,
        which=_fully_equipped_which,
        apps_dir=apps_dir,
        brew_bin=brew_bin,
    )
    results = svc.run()
    # Everything (including the app-bundle and node-symlink checks) is now
    # satisfied under tmp_path, so a fully-equipped machine has zero failures.
    failures = [r for r in results if r.is_failure]
    assert not failures, f"Unexpected failures: {[(r.name, r.hint) for r in failures]}"
