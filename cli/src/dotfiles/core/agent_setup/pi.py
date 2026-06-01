"""agent_setup.pi — port of agents/pi/setup.sh.

Configures Pi (pi.dev / earendil-works) terminal agent:
  - Auto-install pi via npm if binary is absent (match .sh self-heal)
  - Symlink settings.json + models.json from dotfiles
  - Write ~/.pi/agent/AGENTS.md (rules.md + baked rules)
  - Deploy subagents to ~/.pi/agent/agents/
  - Symlink agents/pi/extensions/*.ts → ~/.pi/agent/extensions/
  - pi install npm:pi-superpowers-plus + npm:mitsupi if not present

All paths are injected; Path.home() MUST NOT appear here.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from dotfiles.core.agent_setup.bake_rules import bake_rules
from dotfiles.core.agent_setup.lib import StepResult, deploy_subagents
from dotfiles.core.ports import ProcessRunner

_PI_NPM_PKG = "@earendil-works/pi-coding-agent"


def setup_pi(
    *,
    runner: ProcessRunner,
    home: Path,
    dotfiles_dir: Path,
    which: Callable[[str], str | None] = shutil.which,  # type: ignore[assignment]
) -> list[StepResult]:
    """Configure Pi terminal agent. Returns a list of StepResult."""
    results: list[StepResult] = []

    # --- Ensure pi binary exists; self-heal via npm if missing ---
    if which("pi") is None:
        install_result = _ensure_pi_installed(runner, which)
        results.append(install_result)
        if not install_result.ok:
            return results

    pi_home = home / ".pi" / "agent"
    pi_home.mkdir(parents=True, exist_ok=True)

    results.extend(_setup_config_symlinks(dotfiles_dir, pi_home))
    results.extend(_setup_instructions(dotfiles_dir, pi_home))
    results.extend(deploy_subagents(dotfiles_dir, pi_home / "agents"))
    results.extend(_setup_extensions(dotfiles_dir, pi_home))
    results.extend(_install_pi_packages(runner, which))

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_pi_installed(
    runner: ProcessRunner,
    which: Callable[[str], str | None],
) -> StepResult:
    """Try to npm install -g pi if npm is available; otherwise report failure."""
    if which("npm") is None:
        return StepResult(
            ok=False,
            message=(
                f"Pi not installed and npm unavailable — skipping"
                f" (install: npm install -g {_PI_NPM_PKG})"
            ),
        )
    result = runner.run(("npm", "install", "-g", _PI_NPM_PKG), check=False)
    if result.exit_code == 0:
        return StepResult(ok=True, message=f"Installed pi ({_PI_NPM_PKG})")
    return StepResult(
        ok=False,
        message=f"Pi install failed — run manually: npm install -g {_PI_NPM_PKG}",
        details=result.stderr,
    )


def _setup_config_symlinks(dotfiles_dir: Path, pi_home: Path) -> list[StepResult]:
    """Symlink settings.json + models.json from dotfiles into pi_home."""
    pi_dir = dotfiles_dir / "agents" / "pi"
    results: list[StepResult] = []
    for name in ("settings.json", "models.json"):
        src = pi_dir / name
        dest = pi_home / name
        if not src.is_file():
            results.append(StepResult(ok=False, message=f"Source not found: {src}"))
            continue
        if dest.is_symlink() or dest.exists():
            dest.unlink()
        dest.symlink_to(src)
        results.append(StepResult(ok=True, message=f"Linked Pi {name}"))
    return results


def _setup_instructions(dotfiles_dir: Path, pi_home: Path) -> list[StepResult]:
    """Write ~/.pi/agent/AGENTS.md = rules.md header + baked rules."""
    global_rules = dotfiles_dir / "agents" / "shared" / "rules.md"
    if not global_rules.is_file():
        return []

    rules_content = global_rules.read_text()
    baked = bake_rules(dotfiles_dir)

    content_parts = ["# Global Agent Instructions", "", rules_content, ""]
    if baked:
        content_parts.append(baked)

    agents_md = pi_home / "AGENTS.md"
    agents_md.write_text("\n".join(content_parts), encoding="utf-8")
    return [
        StepResult(ok=True, message="Global instructions + baked rules (~/.pi/agent/AGENTS.md)")
    ]


def _prune_stale_links(directory: Path) -> None:
    """Remove broken symlinks from *directory*."""
    for link in directory.iterdir():
        if link.is_symlink() and not link.exists():
            link.unlink()


def _force_symlink(src: Path, dest: Path) -> None:
    """Create dest → src symlink, replacing any existing file/link."""
    if dest.is_symlink() or dest.exists():
        dest.unlink()
    dest.symlink_to(src)


def _setup_extensions(dotfiles_dir: Path, pi_home: Path) -> list[StepResult]:
    """Symlink agents/pi/extensions/*.ts → pi_home/extensions/; prune stale links."""
    ext_src = dotfiles_dir / "agents" / "pi" / "extensions"
    if not ext_src.is_dir():
        return []

    ext_dest = pi_home / "extensions"
    ext_dest.mkdir(parents=True, exist_ok=True)
    _prune_stale_links(ext_dest)

    results: list[StepResult] = []
    for ts_file in sorted(ext_src.glob("*.ts")):
        if not ts_file.is_file():
            continue
        _force_symlink(ts_file, ext_dest / ts_file.name)
        results.append(StepResult(ok=True, message=f"Linked Pi extension {ts_file.name}"))

    return results


def _pi_package_present(runner: ProcessRunner, pkg_name: str) -> bool:
    """Return True if `pi list` output contains pkg_name."""
    result = runner.run(("pi", "list"), check=False)
    return pkg_name in result.stdout


def _install_pi_packages(
    runner: ProcessRunner,
    which: Callable[[str], str | None],
) -> list[StepResult]:
    """Install pi-superpowers-plus and mitsupi if not already installed."""
    results: list[StepResult] = []
    for pkg in ("pi-superpowers-plus", "mitsupi"):
        if _pi_package_present(runner, pkg):
            results.append(StepResult(ok=True, message=f"{pkg} already installed"))
            continue
        install = runner.run(("pi", "install", f"npm:{pkg}"), check=False)
        if install.exit_code == 0:
            results.append(StepResult(ok=True, message=f"Installed {pkg}"))
        else:
            results.append(
                StepResult(
                    ok=False,
                    message=f"Install failed — run manually: pi install npm:{pkg}",
                    details=install.stderr,
                )
            )
    return results
