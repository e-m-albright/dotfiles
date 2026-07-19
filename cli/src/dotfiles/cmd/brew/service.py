"""Brew package manifest: models, parser, install-plan logic, and install execution.

Reads macos/packages.toml (the source of truth for Homebrew packages) and
provides:
  - Pydantic models for the manifest structure
  - PackageManifest.load(path) to parse the TOML file
  - enabled_packages() to list what should be installed given active flags
  - installed_formulae() / installed_casks() to query the current machine
  - stale_packages() / missing_packages() for install-plan computation
  - add_taps() / install_packages() for install execution
  - install_rust() / install_claude_code() / install_typewhisper() / install_npm_globals()
    for bespoke special installers
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.logging import get_logger
from dotfiles.result import StepResult

_log = get_logger(__name__)


class BrewInventoryError(RuntimeError):
    """Homebrew's installed state could not be read safely."""


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

FeatureFlag = Literal["ai", "productivity", "social"]
PackageKind = Literal["formula", "cask", "auto"]
SpecialMethod = Literal["rustup", "github_dmg", "curl_install"]


class Package(BaseModel):
    """One installable package entry within a section."""

    model_config = ConfigDict(frozen=True)

    name: str
    note: str = ""
    disabled: bool = False
    reason: str = ""
    flag: FeatureFlag | None = None

    @model_validator(mode="after")
    def disabled_requires_reason(self) -> Package:
        if self.disabled and not self.reason.strip():
            raise ValueError(f"disabled package {self.name!r} requires a reason")
        return self


class Section(BaseModel):
    """A named group of packages sharing a kind and optional feature flag."""

    model_config = ConfigDict(frozen=True)

    name: str
    kind: PackageKind
    flag: FeatureFlag | None = None
    packages: list[Package] = []


class SpecialInstaller(BaseModel):
    """Bespoke installer block (rust, typewhisper, claude-code, etc.)."""

    model_config = ConfigDict(frozen=True)

    method: SpecialMethod
    flag: FeatureFlag | None = None
    note: str = ""


class NpmPackage(BaseModel):
    """An npm-global package (no brew formula available)."""

    model_config = ConfigDict(frozen=True)

    name: str
    version: str = ""
    flag: FeatureFlag | None = None
    note: str = ""
    disabled: bool = False
    reason: str = ""

    @model_validator(mode="after")
    def disabled_requires_reason(self) -> NpmPackage:
        if self.disabled and not self.reason.strip():
            raise ValueError(f"disabled npm package {self.name!r} requires a reason")
        return self


class GoPackage(BaseModel):
    """A version-pinned Go command installed with `go install`."""

    model_config = ConfigDict(frozen=True)

    name: str
    module: str
    version: str


class Flags(BaseModel):
    """Feature flag defaults (all true by default; override via env)."""

    model_config = ConfigDict(frozen=True)

    ai: bool = True
    productivity: bool = True
    social: bool = True

    def enabled(self) -> set[FeatureFlag]:
        values: dict[FeatureFlag, bool] = {
            "ai": self.ai,
            "productivity": self.productivity,
            "social": self.social,
        }
        return {name for name, enabled in values.items() if enabled}


class Taps(BaseModel):
    """Homebrew taps to add before installing packages."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    items: list[str] = Field(default=[], alias="list")


class PackageManifest(BaseModel):
    """Full parsed contents of macos/packages.toml."""

    model_config = ConfigDict(frozen=True)

    flags: Flags
    taps: Taps
    sections: list[Section] = []
    specials: dict[str, SpecialInstaller] = {}
    npm_packages: list[NpmPackage] = []
    go_packages: list[GoPackage] = []

    @classmethod
    def load(cls, path: Path) -> PackageManifest:
        """Parse packages.toml and return a validated PackageManifest."""
        with path.open("rb") as fh:
            raw = tomllib.load(fh)

        flags = Flags.model_validate(raw.get("flags", {}))
        taps = Taps.model_validate(raw.get("taps", {}))

        sections = [Section.model_validate(s) for s in raw.get("section", [])]

        specials: dict[str, SpecialInstaller] = {}
        for key, value in raw.get("special", {}).items():
            specials[key] = SpecialInstaller.model_validate(value)

        npm_packages = [NpmPackage.model_validate(n) for n in raw.get("npm_package", [])]
        go_packages = [GoPackage.model_validate(n) for n in raw.get("go_package", [])]

        return cls(
            flags=flags,
            taps=taps,
            sections=sections,
            specials=specials,
            npm_packages=npm_packages,
            go_packages=go_packages,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
) -> list[tuple[str, PackageKind]]:
    """Return (name, kind) pairs for all non-disabled, flag-gated packages.

    A package is included when:
    - Its section flag (if any) is in flags_on
    - Its own flag (if any) is in flags_on
    - disabled = False
    """
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


def installed_formulae(runner: ProcessRunner) -> set[str]:
    """Return the set of formulae currently installed via Homebrew."""
    result = runner.run(("brew", "list", "--formula", "-1"))
    _require_inventory(result.exit_code, result.stderr)
    return {line for line in result.stdout.splitlines() if line.strip()}


def installed_casks(runner: ProcessRunner) -> set[str]:
    """Return the set of casks currently installed via Homebrew."""
    result = runner.run(("brew", "list", "--cask", "-1"))
    _require_inventory(result.exit_code, result.stderr)
    return {line for line in result.stdout.splitlines() if line.strip()}


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
    result = runner.run(("brew", "leaves", "--installed-on-request"))
    _require_inventory(result.exit_code, result.stderr)
    return {line.rsplit("/", 1)[-1] for line in result.stdout.splitlines() if line.strip()}


def _require_inventory(exit_code: int, stderr: str) -> None:
    if exit_code != 0:
        raise BrewInventoryError(stderr.strip() or f"Homebrew inventory failed ({exit_code})")


def stale_packages(
    manifest: PackageManifest,
    runner: ProcessRunner,
) -> list[str]:
    """Return installed packages that are not declared anywhere in the manifest."""
    return InstallPlan.compute(manifest, runner, flags_on=set()).stale


def missing_packages(
    manifest: PackageManifest,
    runner: ProcessRunner,
    *,
    flags_on: set[FeatureFlag],
) -> list[tuple[str, PackageKind]]:
    """Return (name, kind) pairs for enabled packages not currently installed."""
    return InstallPlan.compute(manifest, runner, flags_on=flags_on).missing


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


# ---------------------------------------------------------------------------
# Install execution
# ---------------------------------------------------------------------------


def add_taps(
    manifest: PackageManifest, runner: ProcessRunner, *, dry_run: bool = False
) -> list[StepResult]:
    """Run `brew tap` for each enabled tap. Idempotent — brew tap is a no-op if present."""
    results: list[StepResult] = []
    for tap in manifest.taps.items:
        if dry_run:
            results.append(StepResult(level="info", message=f"DRY RUN: brew tap {tap}"))
            continue
        res = runner.run(("brew", "tap", tap))
        if res.exit_code == 0:
            results.append(StepResult(level="success", message=f"tap {tap}"))
        else:
            # Tolerant like the original brew.sh (`brew tap ... || true`): a
            # transient tap failure (e.g. network) is a warning, not a hard
            # error that aborts the whole `brew install`.
            results.append(
                StepResult(level="warn", message=f"brew tap {tap} failed: {res.stderr.strip()}")
            )
    return results


def _install_formula(name: str, runner: ProcessRunner) -> StepResult:
    res = runner.run(("brew", "install", name))
    if res.exit_code == 0:
        return StepResult(level="success", message=f"installed {name}")
    return StepResult(level="error", message=f"brew install {name} failed")


def _install_cask(name: str, runner: ProcessRunner) -> StepResult:
    res = runner.run(("brew", "install", "--cask", name))
    if res.exit_code == 0:
        return StepResult(level="success", message=f"installed {name}")
    return StepResult(level="error", message=f"brew install --cask {name} failed")


def _install_auto(name: str, runner: ProcessRunner) -> StepResult:
    """Try formula first; fall back to cask."""
    res = runner.run(("brew", "install", name))
    if res.exit_code == 0:
        return StepResult(level="success", message=f"installed {name}")
    res2 = runner.run(("brew", "install", "--cask", name))
    if res2.exit_code == 0:
        return StepResult(level="success", message=f"installed {name} (cask)")
    return StepResult(level="error", message=f"brew install {name} failed (tried formula + cask)")


def _install_one(name: str, kind: PackageKind, runner: ProcessRunner) -> StepResult:
    if kind == "formula":
        return _install_formula(name, runner)
    if kind == "cask":
        return _install_cask(name, runner)
    return _install_auto(name, runner)


def install_packages(
    manifest: PackageManifest,
    runner: ProcessRunner,
    *,
    flags_on: set[FeatureFlag],
    dry_run: bool = False,
) -> list[StepResult]:
    """Install each missing (name, kind) pair from the manifest.

    Already-installed packages are skipped (idempotent).  For kind="auto" we
    try formula first, then cask.  dry_run=True reports what would be done
    without running any mutating command.
    """
    to_install = missing_packages(manifest, runner, flags_on=flags_on)
    if not to_install:
        return [StepResult(level="info", message="All packages already installed")]

    if dry_run:
        return [
            StepResult(level="info", message=f"DRY RUN: brew install {name} ({kind})")
            for name, kind in to_install
        ]

    _log.info("brew_install_start", count=len(to_install))
    results: list[StepResult] = []
    for name, kind in to_install:
        result = _install_one(name, kind, runner)
        if result.level == "error":
            _log.warning("brew_install_failed", package=name, kind=kind)
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# Special installers
# ---------------------------------------------------------------------------


def _download_verified(
    runner: ProcessRunner, *, url: str, sha256: str, directory: Path, filename: str
) -> Path | None:
    target = directory / filename
    if not runner.run(("curl", "-fsSL", "-o", str(target), url)).ok:
        return None
    checked = runner.run(
        ("shasum", "-a", "256", "-c", "-"),
        stdin=f"{sha256}  {target}\n",
    )
    return target if checked.ok else None


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
        installer = _download_verified(
            runner,
            url=_RUSTUP_URL,
            sha256=_RUSTUP_SHA256,
            directory=install_dir,
            filename="rustup-init",
        )
        if installer is None:
            return [StepResult(level="error", message="rustup download verification failed")]
        runner.run(("chmod", "+x", str(installer)))
        installed = runner.run((str(installer), "-y"))
        if not installed.ok:
            return [StepResult(level="error", message="rustup installer failed")]
        return [StepResult(level="success", message="Rust installed via rustup")]
    finally:
        rmtree(install_dir)


_CLAUDE_CODE_CHECK = ("sh", "-c", "command -v claude")
_CLAUDE_CODE_URL = "https://claude.ai/install.sh"
_CLAUDE_CODE_SHA256 = "b3f79015b54c751440a6488f07b1b64f9088742b9052bc1bd356d13108320d2a"
_CLAUDE_CODE_PIN = ("claude", "install", "latest")


def install_claude_code(runner: ProcessRunner) -> list[StepResult]:
    """Install Claude Code via the native installer if not already present.

    Idempotency guard: skips if `claude` is on PATH.
    Pins to `latest` channel after install.
    """
    check = runner.run(_CLAUDE_CODE_CHECK)
    if check.stdout.strip():
        return [StepResult(level="info", message="claude-code already installed — skipping")]

    install_dir = Path(mkdtemp(prefix="dotfiles-claude-"))
    try:
        installer = _download_verified(
            runner,
            url=_CLAUDE_CODE_URL,
            sha256=_CLAUDE_CODE_SHA256,
            directory=install_dir,
            filename="install.sh",
        )
        if installer is None or not runner.run(("bash", str(installer))).ok:
            return [StepResult(level="error", message="claude-code installer failed")]
        runner.run(_CLAUDE_CODE_PIN)
        return [StepResult(level="success", message="claude-code installed")]
    finally:
        rmtree(install_dir)


_TW_APP_PATH = "/Applications/TypeWhisper.app"
_TW_TEAM_ID = "2D8ALY3LCL"
_TW_FETCH_URL = (
    "sh",
    "-c",
    "curl -fsSL 'https://api.github.com/repos/TypeWhisper/typewhisper-mac/releases?per_page=100' "
    "| grep -oE 'https://[^\"]+\\.dmg' "
    "| grep -viE 'daily|-rc|plugin' "
    "| head -1",
)


def install_typewhisper(runner: ProcessRunner, *, dotfiles_dir: Path) -> list[StepResult]:
    """Install TypeWhisper (if absent) and apply its version-controlled config.

    Install is idempotent — skips the DMG download when /Applications/TypeWhisper.app
    exists, but still re-applies the tracked config (macos/typewhisper/) so the repo
    stays the source of truth. Config apply is best-effort and never fails the
    install: if the app is running it can't write live SQLite-backed settings, which
    is reported as a warning, not an error.
    """
    results: list[StepResult] = []

    if Path(_TW_APP_PATH).exists():
        results.append(
            StepResult(level="info", message="TypeWhisper already installed — skipping download")
        )
    else:
        install_steps = _download_typewhisper(runner)
        results.extend(install_steps)
        if any(step.level == "error" for step in install_steps):
            return results  # don't try to configure a failed install

    results.extend(_apply_typewhisper_config(runner, dotfiles_dir))
    return results


def _download_typewhisper(runner: ProcessRunner) -> list[StepResult]:
    """Fetch the latest stable DMG → download → hdiutil attach → cp -R → detach."""
    # Fetch latest stable DMG URL
    url_res = runner.run(_TW_FETCH_URL)
    tw_url = url_res.stdout.strip()
    if not tw_url:
        return [
            StepResult(level="error", message="TypeWhisper: no stable DMG found on GitHub Releases")
        ]

    install_dir = Path(mkdtemp(prefix="dotfiles-typewhisper-"))
    dmg_path = str(install_dir / "TypeWhisper.dmg")
    tw_mount = ""
    try:
        dl_res = runner.run(("curl", "-fsSL", "-o", dmg_path, tw_url))
        if dl_res.exit_code != 0:
            return [StepResult(level="error", message="TypeWhisper: download failed")]

        mount_cmd = (
            f"hdiutil attach {dmg_path!r} -nobrowse -noautoopen 2>/dev/null"
            " | grep -oE '/Volumes/.*' | tail -1"
        )
        tw_mount = runner.run(("sh", "-c", mount_cmd)).stdout.strip()
        if not tw_mount:
            return [StepResult(level="error", message="TypeWhisper: DMG mount failed")]

        app_path = f"{tw_mount}/TypeWhisper.app"
        verified = runner.run(("codesign", "--verify", "--deep", "--strict", app_path))
        identity = runner.run(("codesign", "-dv", "--verbose=4", app_path))
        signature = identity.stdout + identity.stderr
        if not verified.ok or f"TeamIdentifier={_TW_TEAM_ID}" not in signature:
            return [StepResult(level="error", message="TypeWhisper: signature verification failed")]

        copied = runner.run(("cp", "-R", app_path, "/Applications/"))
        if not copied.ok:
            return [StepResult(level="error", message="TypeWhisper: copy to /Applications failed")]
        return [StepResult(level="success", message="TypeWhisper installed")]
    finally:
        if tw_mount:
            runner.run(("hdiutil", "detach", tw_mount, "-quiet"))
        rmtree(install_dir)


def _apply_typewhisper_config(runner: ProcessRunner, dotfiles_dir: Path) -> list[StepResult]:
    """Apply the tracked TypeWhisper config via macos/typewhisper.sh (best-effort)."""
    script = dotfiles_dir / "macos" / "typewhisper.sh"
    if not script.is_file():
        return []
    res = runner.run((str(script), "apply"))
    if res.exit_code == 0:
        return [
            StepResult(level="success", message="TypeWhisper config applied (macos/typewhisper/)")
        ]
    return [
        StepResult(
            level="warn",
            message=(
                "TypeWhisper config not applied (app running?) — quit it and re-run, "
                "or: macos/typewhisper.sh apply --quit --reopen"
            ),
        )
    ]


def install_npm_globals(
    manifest: PackageManifest,
    runner: ProcessRunner,
    *,
    flags_on: set[FeatureFlag],
    dry_run: bool = False,
) -> list[StepResult]:
    """Install npm global packages declared in [[npm_package]] sections.

    Idempotency guard: skips each package if `which <name>` succeeds.
    Flag-gated: packages with a flag are skipped when that flag is not in flags_on.
    """
    steps = (
        _install_one_npm(pkg, runner, flags_on=flags_on, dry_run=dry_run)
        for pkg in manifest.npm_packages
    )
    return [s for s in steps if s is not None]


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
    flags_on: set[FeatureFlag],
    dry_run: bool,
) -> StepResult | None:
    """Install one npm global, or None if it's disabled/flag-gated. Idempotent."""
    if pkg.disabled or not _flag_active(pkg.flag, flags_on):
        return None
    target = f"{pkg.name}@{pkg.version}" if pkg.version else pkg.name
    if dry_run:
        return StepResult(level="info", message=f"DRY RUN: npm install -g {target}")
    check_command = (
        ("npm", "list", "-g", "--depth=0", target)
        if pkg.version
        else ("sh", "-c", f"command -v {pkg.name}")
    )
    check = runner.run(check_command)
    if check.stdout.strip() or check.exit_code == 0:
        return StepResult(level="info", message=f"{pkg.name} already installed — skipping")
    res = runner.run(("npm", "install", "-g", target))
    if res.exit_code == 0:
        return StepResult(level="success", message=f"npm install -g {target}")
    return StepResult(level="error", message=f"npm install -g {target} failed")


def install_specials(
    manifest: PackageManifest,
    runner: ProcessRunner,
    *,
    flags_on: set[FeatureFlag],
    dotfiles_dir: Path,
    dry_run: bool,
) -> list[StepResult]:
    """Run only the special installers declared and enabled by the manifest."""
    results: list[StepResult] = []
    for name, installer in manifest.specials.items():
        if not _flag_active(installer.flag, flags_on):
            continue
        if dry_run:
            results.append(StepResult(level="info", message=f"DRY RUN: install {name}"))
        elif installer.method == "rustup":
            results.extend(install_rust(runner))
        elif installer.method == "curl_install":
            results.extend(install_claude_code(runner))
        else:
            results.extend(install_typewhisper(runner, dotfiles_dir=dotfiles_dir))
    return results


def install_software(
    manifest: PackageManifest,
    runner: ProcessRunner,
    *,
    flags_on: set[FeatureFlag],
    dotfiles_dir: Path,
    dry_run: bool,
) -> list[StepResult]:
    """Reconcile every software source declared by the manifest."""
    results = add_taps(manifest, runner, dry_run=dry_run)
    results.extend(install_packages(manifest, runner, flags_on=flags_on, dry_run=dry_run))
    results.extend(
        install_specials(
            manifest,
            runner,
            flags_on=flags_on,
            dotfiles_dir=dotfiles_dir,
            dry_run=dry_run,
        )
    )
    results.extend(install_npm_globals(manifest, runner, flags_on=flags_on, dry_run=dry_run))
    results.extend(install_go_tools(manifest, runner, dry_run=dry_run))
    return results


def upgrade(runner: ProcessRunner) -> list[StepResult]:
    """Update Homebrew and upgrade all installed formulae + casks, then prune caches.

    Homebrew is the only version-pinning surface in this managed setup, so this is
    the one-shot "bring my packages current" convenience.
    """
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
    cleanup = runner.run(("brew", "cleanup", "--prune=30"))
    if cleanup.ok:
        results.append(StepResult(level="info", message="Pruned caches older than 30 days"))
    else:
        results.append(
            StepResult(level="warn", message="brew cleanup failed", details=cleanup.stderr.strip())
        )
    return results
