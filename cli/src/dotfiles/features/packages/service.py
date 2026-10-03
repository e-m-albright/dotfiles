"""Coordinate the package backends for the selected installation profile."""

from __future__ import annotations

from pathlib import Path

from dotfiles.features.packages.go import install_go_tools
from dotfiles.features.packages.homebrew import add_taps, install_packages
from dotfiles.features.packages.manifest import FeatureFlag, PackageManifest
from dotfiles.features.packages.npm import install_npm_globals
from dotfiles.features.packages.special import install_specials
from dotfiles.ports import ProcessRunner
from dotfiles.result import StepResult


def install_software(
    manifest: PackageManifest,
    runner: ProcessRunner,
    *,
    flags_on: set[FeatureFlag],
    profile: str = "personal",
    dotfiles_dir: Path,
    dry_run: bool,
) -> list[StepResult]:
    """Reconcile software for the personal default or an explicit allowlist profile."""
    selected_taps = None if profile == "personal" else manifest.profiles[profile].taps
    results = add_taps(manifest, runner, selected=selected_taps, dry_run=dry_run)
    results.extend(
        install_packages(manifest, runner, flags_on=flags_on, profile=profile, dry_run=dry_run)
    )
    results.extend(
        install_specials(
            manifest,
            runner,
            flags_on=flags_on,
            profile=profile,
            dotfiles_dir=dotfiles_dir,
            dry_run=dry_run,
        )
    )
    results.extend(
        install_npm_globals(manifest, runner, flags_on=flags_on, profile=profile, dry_run=dry_run)
    )
    if profile == "personal":
        results.extend(install_go_tools(manifest, runner, dry_run=dry_run))
    return results
