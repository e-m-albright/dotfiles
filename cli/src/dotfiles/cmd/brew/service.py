"""Brew package manifest: models, parser, install-plan logic, and install execution.

Reads macos/packages.toml (the source of truth for Homebrew packages) and
provides:
  - Pydantic models for the manifest structure
  - PackageManifest.load(path) to parse the TOML file
  - enabled_packages() to list what should be installed given active flags
  - installed_formulae() / installed_casks() to query the current machine
  - InstallPlan.compute() for install-plan computation (missing + stale)
  - add_taps() / install_packages() for install execution
  - install_rust() / install_npm_globals() for bespoke installers
"""

from __future__ import annotations

import json
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.result import StepResult


class BrewInventoryError(RuntimeError):
    """Homebrew's installed state could not be read safely."""


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

FeatureFlag = Literal["ai", "productivity", "social"]
PackageKind = Literal["formula", "cask", "auto"]
# Records how a non-Homebrew package reaches this host. `python_package` is
# declarative only: that software arrives through this repo's Python dependencies.
SpecialMethod = Literal["rustup", "python_package", "omlx_setup"]

# Tombstone invariant (AGENTS.md): disabled entries retain a *dated* reason.
_TOMBSTONE_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _require_dated_reason(kind: str, name: str, *, disabled: bool, reason: str) -> None:
    if not disabled:
        return
    if not reason.strip():
        raise ValueError(f"disabled {kind} {name!r} requires a reason")
    if not _TOMBSTONE_DATE.search(reason):
        raise ValueError(f"disabled {kind} {name!r} requires a dated reason (YYYY-MM-DD)")


class _ManifestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class Package(_ManifestModel):
    """One installable package entry within a section."""

    name: str
    note: str = ""
    disabled: bool = False
    reason: str = ""
    flag: FeatureFlag | None = None

    @model_validator(mode="after")
    def disabled_requires_reason(self) -> Package:
        _require_dated_reason("package", self.name, disabled=self.disabled, reason=self.reason)
        return self


class Section(_ManifestModel):
    """A named group of packages sharing a kind and optional feature flag."""

    name: str
    kind: PackageKind
    flag: FeatureFlag | None = None
    packages: list[Package] = []


class SpecialInstaller(_ManifestModel):
    """Bespoke installer block for software outside ordinary Homebrew management."""

    method: SpecialMethod
    flag: FeatureFlag | None = None
    note: str = ""
    disabled: bool = False
    reason: str = ""

    @model_validator(mode="after")
    def disabled_requires_reason(self) -> SpecialInstaller:
        _require_dated_reason(
            "special installer", self.method, disabled=self.disabled, reason=self.reason
        )
        return self


class NpmPackage(_ManifestModel):
    """An npm-global package (no brew formula available)."""

    name: str
    version: str = ""
    flag: FeatureFlag | None = None
    note: str = ""
    disabled: bool = False
    reason: str = ""

    @model_validator(mode="after")
    def disabled_requires_reason(self) -> NpmPackage:
        _require_dated_reason("npm package", self.name, disabled=self.disabled, reason=self.reason)
        return self


class GoPackage(_ManifestModel):
    """A version-pinned Go command installed with `go install`."""

    name: str
    module: str
    version: str


class InstallProfile(_ManifestModel):
    """Explicit allowlist for a constrained installation profile."""

    taps: list[str] = []
    formulae: list[str] = []
    casks: list[str] = []
    specials: list[str] = []
    npm_packages: list[str] = []

    @model_validator(mode="after")
    def entries_are_unique(self) -> InstallProfile:
        for kind, names in (
            ("tap", self.taps),
            ("formula", self.formulae),
            ("cask", self.casks),
            ("special", self.specials),
            ("npm package", self.npm_packages),
        ):
            duplicates = sorted({name for name in names if names.count(name) > 1})
            if duplicates:
                raise ValueError(f"duplicate {kind} profile references: {', '.join(duplicates)}")
        return self


ALL_FLAGS: set[FeatureFlag] = {"ai", "productivity", "social"}


class Taps(_ManifestModel):
    """Homebrew taps and narrowly scoped items to trust before installation."""

    items: list[str] = Field(default=[], alias="list")
    trusted_formulae: list[str] = []
    trusted_casks: list[str] = []


class PackageManifest(_ManifestModel):
    """Full parsed contents of macos/packages.toml."""

    taps: Taps
    sections: list[Section] = Field(default=[], alias="section")
    specials: dict[str, SpecialInstaller] = Field(default={}, alias="special")
    npm_packages: list[NpmPackage] = Field(default=[], alias="npm_package")
    go_packages: list[GoPackage] = Field(default=[], alias="go_package")
    profiles: dict[str, InstallProfile] = Field(default={}, alias="profile")

    @model_validator(mode="after")
    def profile_references_resolve(self) -> PackageManifest:
        _validate_profile_references(self)
        return self

    @classmethod
    def load(cls, path: Path) -> PackageManifest:
        """Parse packages.toml and return a validated PackageManifest."""
        with path.open("rb") as fh:
            return cls.model_validate(tomllib.load(fh))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_brew_profile_reference(
    profile_name: str,
    expected: PackageKind,
    name: str,
    by_kind: dict[PackageKind, set[str]],
) -> None:
    if name in by_kind[expected]:
        return
    actual = next((kind for kind, entries in by_kind.items() if name in entries), None)
    if actual:
        raise ValueError(
            f"profile {profile_name!r} lists {name!r} as {expected}, "
            f"but the manifest declares it as {actual}"
        )
    raise ValueError(f"profile {profile_name!r} references unknown {expected} {name!r}")


def _validate_named_profile_references(
    profile_name: str, kind: str, names: list[str], declared: set[str]
) -> None:
    unknown = sorted(set(names) - declared)
    if unknown:
        raise ValueError(
            f"profile {profile_name!r} references unknown {kind}: {', '.join(unknown)}"
        )


def _validate_one_profile(
    profile_name: str,
    profile: InstallProfile,
    declared_taps: set[str],
    by_kind: dict[PackageKind, set[str]],
    special_names: set[str],
    npm_names: set[str],
) -> None:
    _validate_named_profile_references(profile_name, "tap", profile.taps, declared_taps)
    for name in profile.formulae:
        _validate_brew_profile_reference(profile_name, "formula", name, by_kind)
    for name in profile.casks:
        _validate_brew_profile_reference(profile_name, "cask", name, by_kind)
    _validate_named_profile_references(profile_name, "special", profile.specials, special_names)
    _validate_named_profile_references(profile_name, "npm package", profile.npm_packages, npm_names)


def _validate_profile_references(manifest: PackageManifest) -> None:
    by_kind: dict[PackageKind, set[str]] = {"formula": set(), "cask": set(), "auto": set()}
    for section in manifest.sections:
        by_kind[section.kind].update(pkg.name for pkg in section.packages if not pkg.disabled)
    npm_names = {pkg.name for pkg in manifest.npm_packages if not pkg.disabled}
    special_names = {name for name, item in manifest.specials.items() if not item.disabled}
    for profile_name, profile in manifest.profiles.items():
        _validate_one_profile(
            profile_name,
            profile,
            set(manifest.taps.items),
            by_kind,
            special_names,
            npm_names,
        )


def _flag_active(flag: FeatureFlag | None, flags_on: set[FeatureFlag]) -> bool:
    """Return True if flag is None (always active) or present in flags_on."""
    return flag is None or flag in flags_on


def _section_enabled_packages(
    section: Section,
    flags_on: set[FeatureFlag],
) -> list[tuple[str, PackageKind]]:
    """Return enabled (name, kind) pairs from a single section."""
    return [
        (pkg.name, section.kind)
        for pkg in section.packages
        if not pkg.disabled and _flag_active(pkg.flag, flags_on)
    ]


def enabled_packages(
    manifest: PackageManifest,
    *,
    flags_on: set[FeatureFlag],
    profile: str = "personal",
) -> list[tuple[str, PackageKind]]:
    """Return (name, kind) pairs for all non-disabled, flag-gated packages.

    A package is included when:
    - Its section flag (if any) is in flags_on
    - Its own flag (if any) is in flags_on
    - disabled = False
    """
    if profile != "personal":
        selected = manifest.profiles[profile]
        profiled: list[tuple[str, PackageKind]] = []
        profiled.extend((name, "formula") for name in selected.formulae)
        profiled.extend((name, "cask") for name in selected.casks)
        return profiled

    result: list[tuple[str, PackageKind]] = []
    for section in manifest.sections:
        if not _flag_active(section.flag, flags_on):
            continue
        result.extend(_section_enabled_packages(section, flags_on))
    return result


def _all_declared_names(manifest: PackageManifest) -> set[str]:
    """All package names declared in the manifest, enabled OR disabled."""
    return {pkg.name for section in manifest.sections for pkg in section.packages}


# ---------------------------------------------------------------------------
# Runner-backed queries
# ---------------------------------------------------------------------------


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
        declared = _all_declared_names(manifest)
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


# ---------------------------------------------------------------------------
# Special installers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerifiedDownload:
    path: Path | None
    error: str = ""


def _download_verified(
    runner: ProcessRunner, *, url: str, sha256: str, directory: Path, filename: str
) -> VerifiedDownload:
    target = directory / filename
    downloaded = runner.run(("curl", "-fsSL", "-o", str(target), url))
    if not downloaded.ok:
        detail = downloaded.stderr.strip() or f"curl exited {downloaded.exit_code}"
        return VerifiedDownload(None, f"download failed: {detail}")
    checked = runner.run(
        ("shasum", "-a", "256", "-c", "-"),
        stdin=f"{sha256}  {target}\n",
    )
    if checked.ok:
        return VerifiedDownload(target)
    actual = runner.run(("shasum", "-a", "256", str(target))).stdout.split(maxsplit=1)
    actual_hash = actual[0] if actual else "unavailable"
    return VerifiedDownload(None, f"expected {sha256}; downloaded {actual_hash}")


_RUSTUP_CHECK = ("sh", "-c", "command -v rustup || command -v cargo")
_RUSTUP_URL = "https://static.rust-lang.org/rustup/archive/1.28.2/aarch64-apple-darwin/rustup-init"
_RUSTUP_SHA256 = "20ef5516c31b1ac2290084199ba77dbbcaa1406c45c1d978ca68558ef5964ef5"


def install_rust(runner: ProcessRunner) -> list[StepResult]:
    """Install Rust via rustup if not already present.

    Idempotency guard: skips if `rustup` or `cargo` is on PATH.
    Shell startup already sources ``~/.cargo/env`` from the tracked ``.zshenv``;
    this installer must not write through the tracked ``.zprofile`` symlink.
    """
    check = runner.run(_RUSTUP_CHECK)
    if check.stdout.strip():
        return [StepResult(level="info", message="Rust already installed — skipping")]

    install_dir = Path(mkdtemp(prefix="dotfiles-rustup-"))
    try:
        download = _download_verified(
            runner,
            url=_RUSTUP_URL,
            sha256=_RUSTUP_SHA256,
            directory=install_dir,
            filename="rustup-init",
        )
        if download.path is None:
            return [
                StepResult(
                    level="error",
                    message="rustup download verification failed",
                    details=download.error,
                )
            ]
        runner.run(("chmod", "+x", str(download.path)))
        installed = runner.run((str(download.path), "-y"))
        if not installed.ok:
            return [StepResult(level="error", message="rustup installer failed")]
        return [StepResult(level="success", message="Rust installed via rustup")]
    finally:
        rmtree(install_dir)


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
    if not runner.run(("fnm", "install", "--lts")).ok:
        return None, StepResult(level="error", message="fnm failed to install Node.js LTS")
    if not runner.run(("fnm", "default", "lts-latest")).ok:
        return None, StepResult(level="error", message="fnm failed to select Node.js LTS")
    return (
        ("fnm", "exec", "--using", "lts-latest", "npm"),
        StepResult(level="success", message="Node.js LTS installed via fnm"),
    )


def _active_npm_packages(
    manifest: PackageManifest, flags_on: set[FeatureFlag], profile: str
) -> list[NpmPackage]:
    if profile == "personal":
        return [
            pkg
            for pkg in manifest.npm_packages
            if not pkg.disabled and _flag_active(pkg.flag, flags_on)
        ]
    selected = set(manifest.profiles[profile].npm_packages)
    return [pkg for pkg in manifest.npm_packages if not pkg.disabled and pkg.name in selected]


def install_npm_globals(
    manifest: PackageManifest,
    runner: ProcessRunner,
    *,
    flags_on: set[FeatureFlag],
    profile: str = "personal",
    dry_run: bool = False,
) -> list[StepResult]:
    """Install declared npm globals, bootstrapping fnm's LTS runtime when needed."""
    active = _active_npm_packages(manifest, flags_on, profile)
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
    result = runner.run(("npm", "ls", "-g", "--depth=0", "--json"), env=_npm_environment())
    try:
        raw: object = json.loads(result.stdout or "{}")
    except ValueError:
        return {}
    if not isinstance(raw, dict):
        return {}
    deps = cast("dict[str, object]", raw).get("dependencies")
    if not isinstance(deps, dict):
        return {}
    versions: dict[str, str] = {}
    for name, entry in cast("dict[str, object]", deps).items():
        if isinstance(entry, dict):
            versions[name] = str(cast("dict[str, object]", entry).get("version", ""))
    return versions


def npm_drift(manifest: PackageManifest, runner: ProcessRunner) -> list[str]:
    """Enabled npm globals that are missing or at the wrong version.

    packages.toml is the source of truth, so a deleted global or an unapplied
    version bump is reported, not just healed silently on the next full install.
    """
    wanted = [p for p in manifest.npm_packages if not p.disabled]
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


def _install_special(
    name: str,
    installer: SpecialInstaller,
    runner: ProcessRunner,
    *,
    flags_on: set[FeatureFlag],
    dotfiles_dir: Path,
    dry_run: bool,
) -> list[StepResult]:
    if (
        installer.disabled
        or not _flag_active(installer.flag, flags_on)
        or installer.method == "python_package"
    ):
        return []
    if dry_run:
        return [StepResult(level="info", message=f"DRY RUN: install {name}")]
    if installer.method == "rustup":
        return install_rust(runner)
    if installer.method == "omlx_setup":
        script = dotfiles_dir / "macos" / "configure-omlx.sh"
        result = runner.run(("bash", str(script)))
        return [
            StepResult(
                level="success" if result.ok else "error",
                message="configure oMLX grammar, model, and service",
                details=result.stderr.strip(),
            )
        ]
    raise ValueError(f"Unsupported special installer method: {installer.method}")


def install_specials(
    manifest: PackageManifest,
    runner: ProcessRunner,
    *,
    flags_on: set[FeatureFlag],
    profile: str = "personal",
    dotfiles_dir: Path,
    dry_run: bool,
) -> list[StepResult]:
    """Run only the special installers declared and enabled by the manifest."""
    results: list[StepResult] = []
    selected = set(manifest.profiles[profile].specials) if profile != "personal" else None
    for name, installer in manifest.specials.items():
        if selected is not None and name not in selected:
            continue
        results.extend(
            _install_special(
                name,
                installer,
                runner,
                flags_on=ALL_FLAGS if selected is not None else flags_on,
                dotfiles_dir=dotfiles_dir,
                dry_run=dry_run,
            )
        )
    return results


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
