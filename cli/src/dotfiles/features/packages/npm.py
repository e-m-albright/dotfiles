"""npm global package installation and inventory."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import cast

from dotfiles.features.packages.manifest import (
    ALL_FLAGS,
    FeatureFlag,
    NpmPackage,
    PackageInventoryError,
    PackageManifest,
    active_npm_packages,
)
from dotfiles.host import RUNTIMES
from dotfiles.ports import ProcessRunner
from dotfiles.result import StepResult


def _npm_environment() -> dict[str, str]:
    """Keep global CLIs stable across fnm-managed Node version changes."""
    return {**os.environ, "NPM_CONFIG_PREFIX": str(Path.home() / ".npm-global")}


def _npm_runtime(
    runner: ProcessRunner, *, dry_run: bool
) -> tuple[tuple[str, ...] | None, StepResult | None]:
    if dry_run or runner.run(("which", "npm")).ok:
        return ("npm",), None
    if not runner.run(("which", "fnm")).ok:
        return None, StepResult(
            level="error", message="npm globals require npm or fnm, but neither is available"
        )
    if not runner.run(("fnm", "install", RUNTIMES.node)).ok:
        return None, StepResult(
            level="error", message=f"fnm failed to install Node.js {RUNTIMES.node}"
        )
    if not runner.run(("fnm", "default", RUNTIMES.node)).ok:
        return None, StepResult(
            level="error", message=f"fnm failed to select Node.js {RUNTIMES.node}"
        )
    return (
        ("fnm", "exec", "--using", RUNTIMES.node, "npm"),
        StepResult(level="success", message=f"Node.js {RUNTIMES.node} installed via fnm"),
    )


def install_npm_globals(
    manifest: PackageManifest,
    runner: ProcessRunner,
    *,
    flags_on: set[FeatureFlag],
    profile: str = "personal",
    dry_run: bool = False,
) -> list[StepResult]:
    """Install declared npm globals, bootstrapping fnm's Node 26 runtime when needed."""
    active = active_npm_packages(manifest, flags_on, profile)
    if not active:
        return []

    npm_command, runtime_step = _npm_runtime(runner, dry_run=dry_run)
    if npm_command is None:
        return [runtime_step] if runtime_step else []
    results = [runtime_step] if runtime_step else []
    results.extend(
        _install_one_npm(pkg, runner, npm_command=npm_command, dry_run=dry_run) for pkg in active
    )
    return results


def _npm_installed_versions(runner: ProcessRunner) -> dict[str, str]:
    """Globally installed npm packages as {name: version}, from one `npm ls` pass."""
    result = runner.run(
        ("npm", "ls", "-g", "--depth=0", "--json"), env=_npm_environment(), timeout=15
    )
    if not result.ok:
        raise PackageInventoryError(result.stderr.strip() or "npm inventory failed")
    try:
        raw: object = json.loads(result.stdout)
    except ValueError as exc:
        raise PackageInventoryError("npm inventory returned invalid JSON") from exc
    if not isinstance(raw, dict):
        raise PackageInventoryError("npm inventory must be an object")
    deps = cast("dict[str, object]", raw).get("dependencies", {})
    if not isinstance(deps, dict):
        raise PackageInventoryError("npm inventory dependencies must be an object")
    versions: dict[str, str] = {}
    for name, entry in cast("dict[str, object]", deps).items():
        if isinstance(entry, dict):
            versions[name] = str(cast("dict[str, object]", entry).get("version", ""))
    return versions


def npm_drift(
    manifest: PackageManifest, runner: ProcessRunner, *, profile: str = "personal"
) -> list[str]:
    """Enabled npm globals that are missing or at the wrong version.

    packages.toml is the source of truth, so a deleted global or an unapplied
    version bump is reported, not just healed silently on the next full install.
    """
    wanted = active_npm_packages(manifest, ALL_FLAGS, profile)
    if not wanted:
        return []
    installed = _npm_installed_versions(runner)
    drifted: list[str] = []
    for pkg in wanted:
        if pkg.name not in installed:
            drifted.append(f"{pkg.name} (missing)")
        elif pkg.version and installed[pkg.name] != pkg.version:
            drifted.append(
                f"{pkg.name} (installed {installed[pkg.name] or '?'}, want {pkg.version})"
            )
    return drifted


def _install_one_npm(
    pkg: NpmPackage,
    runner: ProcessRunner,
    *,
    npm_command: tuple[str, ...],
    dry_run: bool,
) -> StepResult:
    """Install one active npm global at its declared version."""
    target = f"{pkg.name}@{pkg.version}" if pkg.version else pkg.name
    if dry_run:
        return StepResult(level="info", message=f"DRY RUN: npm install -g {target}")
    # `npm list -g name@version` exits non-zero on a version mismatch even
    # though it still prints the tree root — only the exit code is the signal.
    npm_env = _npm_environment()
    check = runner.run((*npm_command, "list", "-g", "--depth=0", target), env=npm_env)
    if check.exit_code == 0:
        return StepResult(level="info", message=f"{pkg.name} already installed — skipping")
    res = runner.run((*npm_command, "install", "-g", target), env=npm_env)
    if res.exit_code == 0:
        return StepResult(level="success", message=f"npm install -g {target}")
    return StepResult(level="error", message=f"npm install -g {target} failed")
