"""Pinned Go command installation and inventory."""

from __future__ import annotations

from dotfiles.features.packages.manifest import GoPackage, PackageManifest
from dotfiles.ports import ProcessRunner
from dotfiles.result import StepResult


def go_drift(manifest: PackageManifest, runner: ProcessRunner) -> list[str]:
    """Declared Go tools that are missing or not at their pinned version."""
    drifted: list[str] = []
    for pkg in manifest.go_packages:
        located = runner.run(("which", pkg.name))
        if not located.ok:
            drifted.append(f"{pkg.name} (missing)")
            continue
        version = runner.run(("go", "version", "-m", located.stdout.strip()))
        if pkg.version not in version.stdout:
            drifted.append(f"{pkg.name} (want {pkg.version})")
    return drifted


def install_go_tools(
    manifest: PackageManifest, runner: ProcessRunner, *, dry_run: bool
) -> list[StepResult]:
    """Install the exact Go tool versions declared by the manifest."""
    return [_install_one_go(package, runner, dry_run=dry_run) for package in manifest.go_packages]


def _install_one_go(package: GoPackage, runner: ProcessRunner, *, dry_run: bool) -> StepResult:
    target = f"{package.module}@{package.version}"
    if dry_run:
        return StepResult(level="info", message=f"DRY RUN: go install {target}")
    located = runner.run(("which", package.name))
    if located.ok:
        version = runner.run(("go", "version", "-m", located.stdout.strip()))
        if package.version in version.stdout:
            return StepResult(level="info", message=f"{package.name} {package.version} installed")
    installed = runner.run(("go", "install", target))
    return StepResult(level="success" if installed.ok else "error", message=f"go install {target}")
