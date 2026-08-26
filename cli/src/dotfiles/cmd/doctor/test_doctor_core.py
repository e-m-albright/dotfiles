"""Tests for DoctorService checks."""

from pathlib import Path

import pytest

from dotfiles.cmd.brew.service import PackageManifest
from dotfiles.cmd.doctor.models import CheckResult
from dotfiles.cmd.doctor.service import _TOOL_CHECKS, DoctorService
from dotfiles.testing.fakes import FakeProcessRunner, write_tree

_REPO = Path(__file__).resolve().parents[5]


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

    wrong = src.with_name(".zshrc.backup")
    wrong.write_text("# wrong")
    dest.unlink()
    dest.symlink_to(wrong)
    assert (
        _svc(home=tmp_path / "home")._symlink("Configuration", ".zshrc", src, dest).status
        == "missing"
    )


# ---------------------------------------------------------------------------
# run() — full check list
# ---------------------------------------------------------------------------

_ALL_TOOLS = {
    "brew",
    "git",
    "jq",
    "yq",
    "zed",
    "deno",
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
    "codex",
    "tailscale",
    "workbench",
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
    runner.script(("/usr/bin/workbench", "drift", "all"), stdout="OK managed config matches\n")
    return runner


def test_run_groups_sections_and_overall_failure() -> None:
    svc = _svc()  # bare: nothing installed, no tools on which
    results = svc.run()
    sections = [r.section for r in results]
    assert "Core Tools" in sections
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
    (shell_dir / ".zshenv").write_text("# zshenv")
    (shell_dir / ".zprofile").write_text("# zprofile")
    (shell_dir / "amuse.zsh-theme").write_text("# theme")
    (git_dir / ".gitconfig").write_text("[core]\n")
    (git_dir / ".gitignore_global").write_text(".DS_Store\n")

    yazi_src = dotfiles / "terminal" / "yazi"
    yazi_src.mkdir(parents=True)
    (yazi_src / "yazi.toml").write_text("# yazi\n")
    zed_src = dotfiles / "editors" / "zed"
    zed_src.mkdir(parents=True)
    (zed_src / "settings.json").write_text("{}\n")
    (zed_src / "keymap.json").write_text("[]\n")

    home.mkdir(parents=True)
    (home / ".zshrc").symlink_to(shell_dir / ".zshrc")
    (home / ".zshenv").symlink_to(shell_dir / ".zshenv")
    (home / ".gitconfig").symlink_to(git_dir / ".gitconfig")
    (home / ".gitignore_global").symlink_to(git_dir / ".gitignore_global")
    (home / ".zprofile").symlink_to(shell_dir / ".zprofile")
    (home / ".oh-my-zsh" / "custom" / "themes").mkdir(parents=True)
    (home / ".oh-my-zsh" / "custom" / "themes" / "amuse.zsh-theme").symlink_to(
        shell_dir / "amuse.zsh-theme"
    )
    (home / ".config" / "yazi").mkdir(parents=True)
    (home / ".config" / "yazi" / "yazi.toml").symlink_to(yazi_src / "yazi.toml")
    (home / ".config" / "zed").mkdir(parents=True)
    (home / ".config" / "zed" / "settings.json").symlink_to(zed_src / "settings.json")
    (home / ".config" / "zed" / "keymap.json").symlink_to(zed_src / "keymap.json")

    # System-path checks resolved under tmp_path (injected), so no host dependence.
    apps_dir = tmp_path / "Applications"
    apps_dir.mkdir()
    brew_bin = tmp_path / "brew-bin"
    brew_bin.mkdir()
    real_node = tmp_path / "node-real"
    real_node.write_text("#!/bin/sh\n")
    (brew_bin / "node").symlink_to(real_node)  # GUI-app node symlink present

    write_tree(
        home,
        {
            ".gitconfig.local": "[user]\n  email = test@test.com\n",
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


def test_workbench_check_reports_live_drift() -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("/usr/bin/workbench", "drift", "all"), stdout="DRIFT Claude rules\n", exit_code=1
    )
    result = _svc(runner, which=lambda n: "/usr/bin/workbench" if n == "workbench" else None)
    check = result._check_workbench("AI Tools")[0]
    assert check.status == "warn"
    assert check.detail == "DRIFT Claude rules"
    assert check.hint == "Run: workbench sync"


def test_notes_launchers_are_checked_and_fixable(tmp_path: Path) -> None:
    home = tmp_path / "home"
    source = home / "code/private/notes/bin/notes"
    source.parent.mkdir(parents=True)
    source.write_text("#!/bin/sh\n")

    missing = _svc(home=home)._check_notes_launchers("Configuration")
    assert [result.name for result in missing] == ["notes CLI", "nts alias"]
    assert all(result.status == "missing" for result in missing)

    fixed = _svc(home=home, fix=True)._check_notes_launchers("Configuration")
    assert all(result.status == "fixed" for result in fixed)
    assert (home / ".local/bin/notes").resolve() == source.resolve()
    assert (home / ".local/bin/nts").resolve() == source.resolve()


# ---------------------------------------------------------------------------
# packages.toml drift gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "hint"),
    [
        (name, hint)
        for checks in _TOOL_CHECKS.values()
        for name, _command, hint in checks
        if hint.startswith("brew install")
    ],
)
def test_tool_checks_stay_in_sync_with_packages_toml(name: str, hint: str) -> None:
    """Drift gate for the CLAUDE.md invariant: doctor must stay in sync with
    macos/packages.toml (the source of truth for what's installed).

    Every `brew install` hint in the declarative _TOOL_CHECKS table must name a
    package that exists *and is enabled* in the manifest — so disabling or
    renaming a package there breaks this test instead of silently leaving
    doctor checking (and recommending) a tool the repo no longer installs.
    Non-brew hints ("Run install.sh", curl installers) are out of scope.
    """
    manifest = PackageManifest.load(_REPO / "macos" / "packages.toml")
    enabled = {p.name for s in manifest.sections for p in s.packages if not p.disabled}
    cask_ok = {p.name for s in manifest.sections if s.kind in ("cask", "auto") for p in s.packages}

    pkg = hint.split()[-1]
    assert pkg in enabled, (
        f"doctor checks {name!r} with hint {hint!r}, but {pkg!r} is not an "
        "enabled package in macos/packages.toml — update one of them"
    )
    if "--cask" in hint:
        assert pkg in cask_ok, (
            f"doctor hint {hint!r} says --cask but {pkg!r} is not in a "
            "cask/auto section of macos/packages.toml"
        )


def test_runtime_checks_report_degraded_but_usable_states(tmp_path: Path) -> None:
    runner = FakeProcessRunner()
    runner.script(("fnm", "list"), exit_code=1)
    runner.script(("python3", "--version"), stdout="Python 3.13.4\n")

    def which(name: str) -> str | None:
        return f"/usr/bin/{name}" if name in {"fnm", "python3"} else None

    service = DoctorService(
        runner=runner,
        home=tmp_path,
        dotfiles_dir=tmp_path / "dotfiles",
        fix=False,
        which=which,
        apps_dir=tmp_path / "Applications",
        brew_bin=tmp_path / "brew-bin",
    )

    node = service._check_node("Runtimes")[0]
    python = service._check_python("Runtimes")[0]
    node_link = service._check_node_symlink("Runtimes")[0]

    assert (node.status, python.status, node_link.status) == ("warn", "warn", "missing")
    assert python.detail == "Python 3.13.4"


def test_runtime_checks_report_missing_python_without_fnm() -> None:
    service = _svc()
    assert service._check_node("Runtimes") == []
    assert service._check_node_symlink("Runtimes") == []
    assert service._check_python("Runtimes")[0].status == "missing"


def test_node_check_tolerates_inactive_node() -> None:
    runner = FakeProcessRunner()
    runner.script(("fnm", "list"), stdout="lts-latest\n")
    runner.script(("node", "--version"), exit_code=1)
    service = _svc(runner, which=lambda name: "/usr/bin/fnm" if name == "fnm" else None)
    result = service._check_node("Runtimes")[0]
    assert result.status == "ok"
    assert result.detail == "not active"


def test_node_symlink_fix_links_node_and_optional_npx(tmp_path: Path) -> None:
    node = tmp_path / "fnm/node"
    npx = tmp_path / "fnm/npx"
    node.parent.mkdir()
    node.write_text("node")
    npx.write_text("npx")
    paths = {"fnm": str(tmp_path / "fnm/fnm"), "node": str(node), "npx": str(npx)}
    brew_bin = tmp_path / "brew-bin"
    service = DoctorService(
        runner=FakeProcessRunner(),
        home=tmp_path,
        dotfiles_dir=tmp_path / "dotfiles",
        fix=True,
        which=paths.get,
        apps_dir=tmp_path / "Applications",
        brew_bin=brew_bin,
    )

    result = service._check_node_symlink("Runtimes")[0]

    assert result.status == "fixed"
    assert (brew_bin / "node").resolve() == node
    assert (brew_bin / "npx").resolve() == npx


def test_workbench_falls_back_to_checkout_and_handles_empty_drift(tmp_path: Path) -> None:
    command = tmp_path / "code/public/workbench/bin/workbench"
    command.parent.mkdir(parents=True)
    command.write_text("#!/bin/sh\n")
    runner = FakeProcessRunner()
    runner.script((str(command), "drift", "all"), exit_code=1)

    result = _svc(runner, home=tmp_path)._check_workbench("AI Tools")[0]

    assert result.status == "warn"
    assert result.detail == "managed agent config has drifted"


def test_configuration_reports_app_only_states(tmp_path: Path) -> None:
    apps = tmp_path / "Applications"
    (apps / "Tailscale.app").mkdir(parents=True)
    (apps / "Ghostty.app").mkdir()
    service = DoctorService(
        runner=FakeProcessRunner(),
        home=tmp_path / "home",
        dotfiles_dir=tmp_path / "dotfiles",
        fix=False,
        which=lambda _name: None,
        apps_dir=apps,
        brew_bin=tmp_path / "brew-bin",
    )

    assert service._check_essentials()[0].status == "ok"
    ghostty = service._check_ghostty("Configuration")[0]
    assert ghostty.status == "warn"


def test_tool_without_version_output_uses_installed_fallback() -> None:
    result = _svc(which=lambda _name: "/usr/bin/tool")._tool(
        "Core Tools", "Tool", "tool", "install tool"
    )
    assert result.status == "ok"
    assert result.detail == "installed"


def test_fix_backs_up_a_regular_file_instead_of_deleting_it(tmp_path: Path) -> None:
    """--fix on a hand-rolled (non-symlink) config must preserve its content."""
    src = tmp_path / "dotfiles-zshrc"
    src.write_text("# managed")
    dest = tmp_path / ".zshrc"
    dest.write_text("# hand-rolled customizations")

    svc = _svc(fix=True)
    result = svc._symlink("Configuration", ".zshrc", src, dest)

    assert result.status == "fixed"
    assert dest.is_symlink()
    assert dest.resolve() == src.resolve()
    backup = tmp_path / ".zshrc.backup"
    assert backup.read_text() == "# hand-rolled customizations"
