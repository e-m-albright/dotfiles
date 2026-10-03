"""Homebrew inventory, install plans, and maintenance operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from dotfiles.features.packages.manifest import (
    FeatureFlag,
    PackageKind,
    PackageManifest,
    declared_names,
    enabled_packages,
)
from dotfiles.ports import ProcessRunner
from dotfiles.result import StepResult


class BrewInventoryError(RuntimeError):
    """Homebrew's installed state could not be read safely."""


def _strip_version(name: str) -> str:
    """Drop a Homebrew version suffix: ``openssl@3`` -> ``openssl``.

    Homebrew lists a versioned keg under its full name (``openssl@3``) even when
    the manifest declares the unversioned alias (``openssl``). Matching on the
    stripped base keeps declared/installed comparisons alias-aware, the way the
    original brew.sh did via ``brew list <name>``.
    """
    return name.split("@", 1)[0]


def _brew_inventory(runner: ProcessRunner, *args: str) -> set[str]:
    result = runner.run(("brew", *args))
    _require_inventory(result.exit_code, result.stderr)
    return {line for line in result.stdout.splitlines() if line.strip()}


def installed_formulae(runner: ProcessRunner) -> set[str]:
    """Return the set of formulae currently installed via Homebrew."""
    return _brew_inventory(runner, "list", "--formula", "-1")


def installed_casks(runner: ProcessRunner) -> set[str]:
    """Return the set of casks currently installed via Homebrew."""
    return _brew_inventory(runner, "list", "--cask", "-1")


def requested_formulae(runner: ProcessRunner) -> set[str]:
    """Return top-level formulae the user explicitly asked Homebrew to install.

    ``brew leaves --installed-on-request`` excludes transitive dependencies
    (libpng, freetype, harfbuzz, graphite2, pydantic-as-a-semgrep-dep, …). Those
    are Homebrew's bookkeeping, not packages you chose, so they must never be
    reported as "stale" — ``brew autoremove`` reclaims them when their parents go.
    """
    # `brew leaves` returns tap-qualified names for tapped formulae
    # (ariga/tap/atlas), while packages.toml declares the short name (atlas).
    # Strip the tap prefix so declared-matching stays aligned with installed_*.
    return {
        line.rsplit("/", 1)[-1]
        for line in _brew_inventory(runner, "leaves", "--installed-on-request")
    }


def _require_inventory(exit_code: int, stderr: str) -> None:
    if exit_code != 0:
        raise BrewInventoryError(stderr.strip() or f"Homebrew inventory failed ({exit_code})")


def stale_taps(manifest: PackageManifest, runner: ProcessRunner) -> list[str]:
    """Return installed third-party taps that are not declared in the manifest."""
    installed = _brew_inventory(runner, "tap")
    return sorted(installed - set(manifest.taps.items))


@dataclass(frozen=True)
class PruneCandidate:
    """An installed Homebrew package retained as a disabled tombstone."""

    name: str
    kind: Literal["formula", "cask"]


@dataclass(frozen=True)
class InstallPlan:
    """Computed install plan: what's missing vs stale on this machine."""

    missing: list[tuple[str, PackageKind]]
    stale: list[str]

    @classmethod
    def compute(
        cls,
        manifest: PackageManifest,
        runner: ProcessRunner,
        *,
        flags_on: set[FeatureFlag],
    ) -> InstallPlan:
        formulae = installed_formulae(runner)
        casks = installed_casks(runner)
        installed = formulae | casks
        satisfied = installed | {_strip_version(name) for name in installed}
        wanted = enabled_packages(manifest, flags_on=flags_on)
        missing: list[tuple[str, PackageKind]] = [
            (name, kind) for name, kind in wanted if name not in satisfied
        ]
        declared = declared_names(manifest)
        requested = requested_formulae(runner)
        stale = sorted(
            name
            for name in (requested | casks)
            if name not in declared and _strip_version(name) not in declared
        )
        return cls(missing=missing, stale=stale)


def _installed_prune_kind(
    name: str,
    declared_kind: PackageKind,
    formulae: set[str],
    casks: set[str],
) -> Literal["formula", "cask"] | None:
    if declared_kind != "cask" and name in formulae:
        return "formula"
    if declared_kind != "formula" and name in casks:
        return "cask"
    return None


def prune_candidates(
    manifest: PackageManifest,
    runner: ProcessRunner,
) -> list[PruneCandidate]:
    """Return installed packages whose manifest entries are disabled tombstones."""
    formulae = installed_formulae(runner)
    casks = installed_casks(runner)
    candidates: list[PruneCandidate] = []
    for section in manifest.sections:
        for package in (package for package in section.packages if package.disabled):
            kind = _installed_prune_kind(package.name, section.kind, formulae, casks)
            if kind is not None:
                candidates.append(PruneCandidate(name=package.name, kind=kind))
    return candidates


def uninstall_prune_candidates(
    candidates: list[PruneCandidate],
    runner: ProcessRunner,
) -> list[StepResult]:
    """Uninstall candidates without altering their manifest tombstones."""
    results: list[StepResult] = []
    for candidate in candidates:
        command = (
            ("brew", "uninstall", candidate.name)
            if candidate.kind == "formula"
            else ("brew", "uninstall", "--cask", candidate.name)
        )
        result = runner.run(command)
        if result.ok:
            results.append(StepResult(level="success", message=f"uninstalled {candidate.name}"))
        else:
            results.append(
                StepResult(
                    level="error",
                    message=f"{' '.join(command)} failed: {result.stderr.strip()}",
                )
            )
    return results


# ---------------------------------------------------------------------------
# Install execution
# ---------------------------------------------------------------------------


def _add_tap(tap: str, runner: ProcessRunner, *, dry_run: bool) -> StepResult:
    command = ("brew", "tap", tap)
    if dry_run:
        return StepResult(level="info", message=f"DRY RUN: {' '.join(command)}")
    res = runner.run(command)
    if res.exit_code == 0:
        return StepResult(level="success", message=f"tap {tap}")
    # A transient tap failure should not hide independent core package installs;
    # any package from this tap will fail clearly later.
    return StepResult(level="warn", message=f"brew tap {tap} failed: {res.stderr.strip()}")


def _trust_tap_item(
    kind: str,
    item: str,
    runner: ProcessRunner,
    *,
    dry_run: bool,
) -> StepResult:
    command = ("brew", "trust", f"--{kind}", item)
    if dry_run:
        return StepResult(level="info", message=f"DRY RUN: {' '.join(command)}")
    res = runner.run(command)
    if res.exit_code == 0:
        return StepResult(level="success", message=f"trust {kind} {item}")
    return StepResult(level="error", message=f"{' '.join(command)} failed: {res.stderr.strip()}")


def add_taps(
    manifest: PackageManifest,
    runner: ProcessRunner,
    *,
    selected: list[str] | None = None,
    dry_run: bool = False,
) -> list[StepResult]:
    """Add all declared taps, or only an explicit profile subset."""
    taps = manifest.taps.items if selected is None else selected
    results = [_add_tap(tap, runner, dry_run=dry_run) for tap in taps]
    if selected is not None:
        return results
    for kind, items in (
        ("formula", manifest.taps.trusted_formulae),
        ("cask", manifest.taps.trusted_casks),
    ):
        results.extend(_trust_tap_item(kind, item, runner, dry_run=dry_run) for item in items)
    return results


def _install_formula(name: str, runner: ProcessRunner) -> StepResult:
    res = runner.run(("brew", "install", name), capture_output=False)
    if res.exit_code == 0:
        return StepResult(level="success", message=f"installed {name}")
    return StepResult(level="error", message=f"brew install {name} failed")


def _install_cask(name: str, runner: ProcessRunner) -> StepResult:
    res = runner.run(("brew", "install", "--cask", name), capture_output=False)
    if res.exit_code == 0:
        return StepResult(level="success", message=f"installed {name}")
    return StepResult(level="error", message=f"brew install --cask {name} failed")


def _install_auto(name: str, runner: ProcessRunner) -> StepResult:
    """Try formula first; fall back to cask."""
    res = runner.run(("brew", "install", name), capture_output=False)
    if res.exit_code == 0:
        return StepResult(level="success", message=f"installed {name}")
    res2 = runner.run(("brew", "install", "--cask", name), capture_output=False)
    if res2.exit_code == 0:
        return StepResult(level="success", message=f"installed {name} (cask)")
    return StepResult(level="error", message=f"brew install {name} failed (tried formula + cask)")


def _install_one(name: str, kind: PackageKind, runner: ProcessRunner) -> StepResult:
    if kind == "formula":
        return _install_formula(name, runner)
    if kind == "cask":
        return _install_cask(name, runner)
    return _install_auto(name, runner)


def _missing_profile_packages(
    manifest: PackageManifest, runner: ProcessRunner, profile: str
) -> list[tuple[str, PackageKind]]:
    wanted = enabled_packages(manifest, flags_on=set(), profile=profile)
    formulae = installed_formulae(runner)
    casks = installed_casks(runner)
    return [
        (name, kind)
        for name, kind in wanted
        if name not in (formulae if kind == "formula" else casks)
    ]


def install_packages(
    manifest: PackageManifest,
    runner: ProcessRunner,
    *,
    flags_on: set[FeatureFlag],
    profile: str = "personal",
    dry_run: bool = False,
) -> list[StepResult]:
    """Install each missing (name, kind) pair from the manifest.

    Already-installed packages are skipped (idempotent).  For kind="auto" we
    try formula first, then cask.  dry_run=True reports what would be done
    without running any mutating command.
    """
    to_install: list[tuple[str, PackageKind]]
    if profile == "personal":
        to_install = InstallPlan.compute(manifest, runner, flags_on=flags_on).missing
    else:
        to_install = _missing_profile_packages(manifest, runner, profile)
    if not to_install:
        return [StepResult(level="info", message="All packages already installed")]

    if dry_run:
        return [
            StepResult(level="info", message=f"DRY RUN: brew install {name} ({kind})")
            for name, kind in to_install
        ]

    results: list[StepResult] = []
    for name, kind in to_install:
        results.append(_install_one(name, kind, runner))
    return results


def cleanup(runner: ProcessRunner) -> list[StepResult]:
    """Prune Homebrew caches older than 30 days."""
    result = runner.run(("brew", "cleanup", "--prune=30"))
    if result.ok:
        return [StepResult(level="success", message="Pruned caches older than 30 days")]
    return [StepResult(level="error", message="brew cleanup failed", details=result.stderr.strip())]


def upgrade(runner: ProcessRunner) -> list[StepResult]:
    """Update Homebrew and upgrade all installed formulae + casks, then prune caches."""
    results: list[StepResult] = []
    update = runner.run(("brew", "update"))
    if update.ok:
        results.append(StepResult(level="success", message="Updated Homebrew index"))
    else:
        results.append(
            StepResult(level="error", message="brew update failed", details=update.stderr.strip())
        )
        return results
    res = runner.run(("brew", "upgrade"))
    if res.ok:
        results.append(StepResult(level="success", message="Upgraded formulae + casks"))
    else:
        results.append(
            StepResult(level="error", message="brew upgrade failed", details=res.stderr.strip())
        )
    cleanup_steps = cleanup(runner)
    results.extend(
        StepResult(level="warn", message=step.message, details=step.details)
        if step.level == "error"
        else step
        for step in cleanup_steps
    )
    return results
