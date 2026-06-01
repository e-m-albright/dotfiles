"""Tests for core/agent_setup/pi.py.

All tests use tmp_path for home + dotfiles_dir; no real home is touched.
FakeProcessRunner is used for all subprocess calls.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dotfiles.core.agent_setup.pi import setup_pi
from tests.fakes import FakeProcessRunner, write_tree

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

RULES_MD = "# Shared Agentic Rules\n\nSome rules here.\n"
PROCESS_RULE = """\
---
description: A test rule
alwaysApply: true
---

# Rule Body

Rule content.
"""
SETTINGS_JSON = '{"model": "default"}'
MODELS_JSON = '{"providers": []}'


@pytest.fixture
def dotfiles(tmp_path: Path) -> Path:
    d = tmp_path / "dotfiles"
    write_tree(
        d,
        {
            "agents/shared/rules.md": RULES_MD,
            "agents/pi/settings.json": SETTINGS_JSON,
            "agents/pi/models.json": MODELS_JSON,
            "agents/pi/extensions/git-status.ts": "// git status extension",
            "agents/pi/extensions/safe-git.ts": "// safe git extension",
            ".ai/rules/process/global-process.mdc": PROCESS_RULE,
            ".ai/agents/debugger.md": "# Debugger",
        },
    )
    return d


def _runner_pi_present() -> FakeProcessRunner:
    """Runner that reports both pi packages as NOT installed (empty stdout)."""
    r = FakeProcessRunner()
    # pi list returns empty → packages need installing
    r.script(("pi", "list"), stdout="")
    return r


def _runner_pi_packages_installed() -> FakeProcessRunner:
    """Runner where pi list shows both packages already present."""
    r = FakeProcessRunner()
    r.script(("pi", "list"), stdout="pi-superpowers-plus mitsupi")
    return r


def _which_pi(name: str) -> str | None:
    return "/usr/bin/pi" if name == "pi" else None


def _which_none(_name: str) -> str | None:
    return None


def _which_npm_only(name: str) -> str | None:
    return "/usr/bin/npm" if name == "npm" else None


# ---------------------------------------------------------------------------
# pi absent, npm absent → skip
# ---------------------------------------------------------------------------


class TestPiAbsentNpmAbsent:
    def test_returns_failure_result(self, dotfiles: Path, home: Path) -> None:
        r = FakeProcessRunner()
        results = setup_pi(runner=r, home=home, dotfiles_dir=dotfiles, which=_which_none)
        assert len(results) == 1
        assert not results[0].ok
        assert "npm unavailable" in results[0].message

    def test_no_pi_home_created(self, dotfiles: Path, home: Path) -> None:
        setup_pi(runner=FakeProcessRunner(), home=home, dotfiles_dir=dotfiles, which=_which_none)
        assert not (home / ".pi").exists()

    def test_no_npm_install_called(self, dotfiles: Path, home: Path) -> None:
        r = FakeProcessRunner()
        setup_pi(runner=r, home=home, dotfiles_dir=dotfiles, which=_which_none)
        assert r.calls == []


# ---------------------------------------------------------------------------
# pi absent, npm present → install
# ---------------------------------------------------------------------------


class TestPiAbsentNpmPresent:
    def test_calls_npm_install_g(self, dotfiles: Path, home: Path) -> None:
        r = FakeProcessRunner()
        # npm install succeeds; then pi list + installs
        r.script(("pi", "list"), stdout="pi-superpowers-plus mitsupi")
        setup_pi(runner=r, home=home, dotfiles_dir=dotfiles, which=_which_npm_only)
        assert ("npm", "install", "-g", "@earendil-works/pi-coding-agent") in r.calls

    def test_reports_install_success(self, dotfiles: Path, home: Path) -> None:
        r = FakeProcessRunner()
        r.script(("pi", "list"), stdout="pi-superpowers-plus mitsupi")
        results = setup_pi(runner=r, home=home, dotfiles_dir=dotfiles, which=_which_npm_only)
        install_result = results[0]
        assert install_result.ok
        assert "Installed pi" in install_result.message

    def test_stops_on_npm_install_failure(self, dotfiles: Path, home: Path) -> None:
        r = FakeProcessRunner()
        r.script(
            ("npm", "install", "-g", "@earendil-works/pi-coding-agent"),
            exit_code=1,
            stderr="npm error",
        )
        results = setup_pi(runner=r, home=home, dotfiles_dir=dotfiles, which=_which_npm_only)
        assert len(results) == 1
        assert not results[0].ok
        assert "run manually" in results[0].message


# ---------------------------------------------------------------------------
# pi present — config symlinks
# ---------------------------------------------------------------------------


class TestConfigSymlinks:
    def _run(self, dotfiles: Path, home: Path) -> list:
        r = _runner_pi_packages_installed()
        return setup_pi(runner=r, home=home, dotfiles_dir=dotfiles, which=_which_pi)

    def test_creates_pi_home_dir(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        assert (home / ".pi" / "agent").is_dir()

    def test_settings_json_symlinked(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        link = home / ".pi" / "agent" / "settings.json"
        assert link.is_symlink()
        assert link.read_text() == SETTINGS_JSON

    def test_models_json_symlinked(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        link = home / ".pi" / "agent" / "models.json"
        assert link.is_symlink()
        assert link.read_text() == MODELS_JSON

    def test_symlinks_point_into_dotfiles(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        for name in ("settings.json", "models.json"):
            link = home / ".pi" / "agent" / name
            assert link.resolve() == (dotfiles / "agents" / "pi" / name).resolve()


# ---------------------------------------------------------------------------
# pi present — AGENTS.md
# ---------------------------------------------------------------------------


class TestAgentsMd:
    def _run(self, dotfiles: Path, home: Path) -> list:
        r = _runner_pi_packages_installed()
        return setup_pi(runner=r, home=home, dotfiles_dir=dotfiles, which=_which_pi)

    def test_writes_agents_md(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        assert (home / ".pi" / "agent" / "AGENTS.md").is_file()

    def test_agents_md_starts_with_header(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        content = (home / ".pi" / "agent" / "AGENTS.md").read_text()
        assert content.startswith("# Shared Agentic Rules")

    def test_agents_md_contains_rules_md(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        content = (home / ".pi" / "agent" / "AGENTS.md").read_text()
        assert "Shared Agentic Rules" in content


# ---------------------------------------------------------------------------
# pi present — subagents
# ---------------------------------------------------------------------------


class TestSubagents:
    def test_deploys_subagents(self, dotfiles: Path, home: Path) -> None:
        r = _runner_pi_packages_installed()
        setup_pi(runner=r, home=home, dotfiles_dir=dotfiles, which=_which_pi)
        assert (home / ".pi" / "agent" / "agents" / "debugger.md").is_file()


# ---------------------------------------------------------------------------
# pi present — extensions
# ---------------------------------------------------------------------------


class TestExtensions:
    def _run(self, dotfiles: Path, home: Path) -> list:
        r = _runner_pi_packages_installed()
        return setup_pi(runner=r, home=home, dotfiles_dir=dotfiles, which=_which_pi)

    def test_creates_extensions_dir(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        assert (home / ".pi" / "agent" / "extensions").is_dir()

    def test_ts_files_symlinked(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        ext_dir = home / ".pi" / "agent" / "extensions"
        assert (ext_dir / "git-status.ts").is_symlink()
        assert (ext_dir / "safe-git.ts").is_symlink()

    def test_symlinks_point_into_dotfiles(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        ext_dir = home / ".pi" / "agent" / "extensions"
        for name in ("git-status.ts", "safe-git.ts"):
            assert (ext_dir / name).resolve() == (
                dotfiles / "agents" / "pi" / "extensions" / name
            ).resolve()

    def test_stale_symlinks_pruned(self, dotfiles: Path, home: Path) -> None:
        """Stale symlinks (broken targets) should be removed."""
        ext_dir = home / ".pi" / "agent" / "extensions"
        ext_dir.mkdir(parents=True)
        stale = ext_dir / "old-extension.ts"
        stale.symlink_to("/nonexistent/path.ts")
        self._run(dotfiles, home)
        assert not stale.exists()

    def test_idempotent_symlinks(self, dotfiles: Path, home: Path) -> None:
        self._run(dotfiles, home)
        results = self._run(dotfiles, home)
        assert all(r.ok for r in results)


# ---------------------------------------------------------------------------
# pi present — pi package installs
# ---------------------------------------------------------------------------


class TestPiPackageInstalls:
    def test_calls_pi_install_for_superpowers(self, dotfiles: Path, home: Path) -> None:
        r = _runner_pi_present()
        setup_pi(runner=r, home=home, dotfiles_dir=dotfiles, which=_which_pi)
        assert ("pi", "install", "npm:pi-superpowers-plus") in r.calls

    def test_calls_pi_install_for_mitsupi(self, dotfiles: Path, home: Path) -> None:
        r = _runner_pi_present()
        setup_pi(runner=r, home=home, dotfiles_dir=dotfiles, which=_which_pi)
        assert ("pi", "install", "npm:mitsupi") in r.calls

    def test_skips_install_when_already_present(self, dotfiles: Path, home: Path) -> None:
        r = _runner_pi_packages_installed()
        results = setup_pi(runner=r, home=home, dotfiles_dir=dotfiles, which=_which_pi)
        pkg_results = [res for res in results if "already installed" in res.message]
        assert len(pkg_results) == 2

    def test_no_pi_install_calls_when_packages_present(self, dotfiles: Path, home: Path) -> None:
        r = _runner_pi_packages_installed()
        setup_pi(runner=r, home=home, dotfiles_dir=dotfiles, which=_which_pi)
        pi_installs = [c for c in r.calls if c[:2] == ("pi", "install")]
        assert pi_installs == []

    def test_install_failure_reported(self, dotfiles: Path, home: Path) -> None:
        r = FakeProcessRunner()
        r.script(("pi", "list"), stdout="")
        r.script(("pi", "install", "npm:pi-superpowers-plus"), exit_code=1, stderr="err")
        r.script(("pi", "install", "npm:mitsupi"), exit_code=1, stderr="err")
        results = setup_pi(runner=r, home=home, dotfiles_dir=dotfiles, which=_which_pi)
        failed = [res for res in results if not res.ok and "run manually" in res.message]
        assert len(failed) == 2


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_running_twice_is_safe(self, dotfiles: Path, home: Path) -> None:
        r = _runner_pi_packages_installed()
        setup_pi(runner=r, home=home, dotfiles_dir=dotfiles, which=_which_pi)
        r2 = _runner_pi_packages_installed()
        results = setup_pi(runner=r2, home=home, dotfiles_dir=dotfiles, which=_which_pi)
        assert all(r.ok for r in results)
