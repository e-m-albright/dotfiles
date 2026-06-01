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
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dotfiles.core.models import StepResult
from dotfiles.core.ports import ProcessRunner

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Package(BaseModel):
    """One installable package entry within a section."""

    model_config = ConfigDict(frozen=True)

    name: str
    note: str = ""
    disabled: bool = False
    reason: str = ""
    flag: str | None = None


class Section(BaseModel):
    """A named group of packages sharing a kind and optional feature flag."""

    model_config = ConfigDict(frozen=True)

    name: str
    kind: Literal["formula", "cask", "auto"]
    flag: str | None = None
    packages: list[Package] = []


class SpecialInstaller(BaseModel):
    """Bespoke installer block (rust, typewhisper, claude-code, etc.)."""

    model_config = ConfigDict(frozen=True)

    # The key under [special.*] becomes the installer name; remaining fields
    # are stored loosely so the model doesn't need to know every installer's
    # shape up front.
    method: str
    flag: str | None = None
    extra: dict[str, Any] = {}

    @model_validator(mode="before")
    @classmethod
    def absorb_extra(cls, data: dict[str, Any]) -> dict[str, Any]:
        known = {"method", "flag"}
        extra = {k: v for k, v in data.items() if k not in known}
        return {
            "method": data.get("method", ""),
            "flag": data.get("flag"),
            "extra": extra,
        }


class NpmPackage(BaseModel):
    """An npm-global package (no brew formula available)."""

    model_config = ConfigDict(frozen=True)

    name: str
    flag: str | None = None
    note: str = ""


class Flags(BaseModel):
    """Feature flag defaults (all true by default; override via env)."""

    model_config = ConfigDict(frozen=True)

    ai: bool = True
    productivity: bool = True
    social: bool = True


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

        return cls(
            flags=flags,
            taps=taps,
            sections=sections,
            specials=specials,
            npm_packages=npm_packages,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _flag_active(flag: str | None, flags_on: set[str]) -> bool:
    """Return True if flag is None (always active) or present in flags_on."""
    return flag is None or flag in flags_on


def _section_enabled_packages(
    section: Section,
    flags_on: set[str],
) -> list[tuple[str, str]]:
    """Return enabled (name, kind) pairs from a single section."""
    return [
        (pkg.name, section.kind)
        for pkg in section.packages
        if not pkg.disabled and _flag_active(pkg.flag, flags_on)
    ]


def enabled_packages(
    manifest: PackageManifest,
    *,
    flags_on: set[str],
) -> list[tuple[str, str]]:
    """Return (name, kind) pairs for all non-disabled, flag-gated packages.

    A package is included when:
    - Its section flag (if any) is in flags_on
    - Its own flag (if any) is in flags_on
    - disabled = False
    """
    result: list[tuple[str, str]] = []
    for section in manifest.sections:
        if not _flag_active(section.flag, flags_on):
            continue
        result.extend(_section_enabled_packages(section, flags_on))
    return result


def _all_declared_names(manifest: PackageManifest) -> set[str]:
    """All package names declared in the manifest, enabled OR disabled."""
    names: set[str] = set()
    for section in manifest.sections:
        for pkg in section.packages:
            names.add(pkg.name)
    return names


# ---------------------------------------------------------------------------
# Runner-backed queries
# ---------------------------------------------------------------------------


def installed_formulae(runner: ProcessRunner) -> set[str]:
    """Return the set of formulae currently installed via Homebrew."""
    result = runner.run(("brew", "list", "--formula", "-1"))
    return {line for line in result.stdout.splitlines() if line.strip()}


def installed_casks(runner: ProcessRunner) -> set[str]:
    """Return the set of casks currently installed via Homebrew."""
    result = runner.run(("brew", "list", "--cask", "-1"))
    return {line for line in result.stdout.splitlines() if line.strip()}


def stale_packages(
    manifest: PackageManifest,
    runner: ProcessRunner,
    *,
    flags_on: set[str],
) -> list[str]:
    """Return installed packages that are not declared anywhere in the manifest.

    "Stale" means installed on this machine but not mentioned at all in
    packages.toml (not even as disabled). A disabled package is intentionally
    absent from the install set but is still declared — so it is NOT stale.
    """
    declared = _all_declared_names(manifest)
    formulae = installed_formulae(runner)
    casks = installed_casks(runner)
    installed = formulae | casks
    stale = sorted(installed - declared)
    return stale


def missing_packages(
    manifest: PackageManifest,
    runner: ProcessRunner,
    *,
    flags_on: set[str],
) -> list[tuple[str, str]]:
    """Return (name, kind) pairs for enabled packages not currently installed."""
    formulae = installed_formulae(runner)
    casks = installed_casks(runner)
    installed = formulae | casks
    wanted = enabled_packages(manifest, flags_on=flags_on)
    return [(name, kind) for name, kind in wanted if name not in installed]


# ---------------------------------------------------------------------------
# Install execution
# ---------------------------------------------------------------------------


def add_taps(manifest: PackageManifest, runner: ProcessRunner) -> list[StepResult]:
    """Run `brew tap` for each enabled tap. Idempotent — brew tap is a no-op if present."""
    results: list[StepResult] = []
    for tap in manifest.taps.items:
        res = runner.run(("brew", "tap", tap))
        if res.exit_code == 0:
            results.append(StepResult(level="success", message=f"tap {tap}"))
        else:
            results.append(
                StepResult(level="error", message=f"brew tap {tap} failed: {res.stderr.strip()}")
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


def _install_one(name: str, kind: str, runner: ProcessRunner) -> StepResult:
    if kind == "formula":
        return _install_formula(name, runner)
    if kind == "cask":
        return _install_cask(name, runner)
    return _install_auto(name, runner)


def install_packages(
    manifest: PackageManifest,
    runner: ProcessRunner,
    *,
    flags_on: set[str],
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

    return [_install_one(name, kind, runner) for name, kind in to_install]


# ---------------------------------------------------------------------------
# Special installers
# ---------------------------------------------------------------------------

_RUSTUP_CHECK = ("sh", "-c", "command -v rustup || command -v cargo")
_RUSTUP_INSTALL = (
    "sh",
    "-c",
    "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
)
_CARGO_ENV_LINE = '[[ -f "$HOME/.cargo/env" ]] && source "$HOME/.cargo/env"'


def install_rust(runner: ProcessRunner) -> list[StepResult]:
    """Install Rust via rustup if not already present.

    Idempotency guard: skips if `rustup` or `cargo` is on PATH.
    Post-install: ensures ~/.zprofile sources ~/.cargo/env.
    """
    check = runner.run(_RUSTUP_CHECK)
    if check.stdout.strip():
        return [StepResult(level="info", message="Rust already installed — skipping")]

    res = runner.run(_RUSTUP_INSTALL)
    if res.exit_code != 0:
        return [StepResult(level="error", message=f"rustup installer failed: {res.stderr.strip()}")]

    # Idempotent .zprofile patch via pathlib (no runner needed for file I/O)
    zprofile = Path.home() / ".zprofile"
    try:
        existing = zprofile.read_text() if zprofile.exists() else ""
        if ".cargo/env" not in existing:
            with zprofile.open("a") as fh:
                fh.write(f"\n# Rust (rustup)\n{_CARGO_ENV_LINE}\n")
    except OSError:
        pass  # Non-fatal; user can add manually

    return [StepResult(level="success", message="Rust installed via rustup")]


_CLAUDE_CODE_CHECK = ("sh", "-c", "command -v claude")
_CLAUDE_CODE_INSTALL = ("sh", "-c", "curl -fsSL https://claude.ai/install.sh | bash")
_CLAUDE_CODE_PIN = ("claude", "install", "latest")


def install_claude_code(runner: ProcessRunner) -> list[StepResult]:
    """Install Claude Code via the native installer if not already present.

    Idempotency guard: skips if `claude` is on PATH.
    Pins to `latest` channel after install.
    """
    check = runner.run(_CLAUDE_CODE_CHECK)
    if check.stdout.strip():
        return [StepResult(level="info", message="claude-code already installed — skipping")]

    res = runner.run(_CLAUDE_CODE_INSTALL)
    if res.exit_code != 0:
        return [
            StepResult(level="error", message=f"claude-code installer failed: {res.stderr.strip()}")
        ]

    # Pin to latest (non-fatal if this fails)
    runner.run(_CLAUDE_CODE_PIN)

    return [StepResult(level="success", message="claude-code installed")]


_TW_APP_PATH = "/Applications/TypeWhisper.app"
_TW_FETCH_URL = (
    "sh",
    "-c",
    "curl -fsSL 'https://api.github.com/repos/TypeWhisper/typewhisper-mac/releases?per_page=100' "
    "| grep -oE 'https://[^\"]+\\.dmg' "
    "| grep -viE 'daily|-rc|plugin' "
    "| head -1",
)
_TW_DMG_PATH = "/tmp/TypeWhisper-install.dmg"


def install_typewhisper(runner: ProcessRunner) -> list[StepResult]:
    """Install TypeWhisper from GitHub Releases DMG if not already present.

    Idempotency guard: skips if /Applications/TypeWhisper.app exists.
    Flow: fetch latest stable DMG URL → download → hdiutil attach → cp -R → detach.
    """
    if Path(_TW_APP_PATH).exists():
        return [StepResult(level="info", message="TypeWhisper already installed — skipping")]

    # Fetch latest stable DMG URL
    url_res = runner.run(_TW_FETCH_URL)
    tw_url = url_res.stdout.strip()
    if not tw_url:
        return [
            StepResult(level="error", message="TypeWhisper: no stable DMG found on GitHub Releases")
        ]

    # Download
    dl_res = runner.run(("sh", "-c", f"curl -fsSL -o {_TW_DMG_PATH!r} {tw_url!r}"))
    if dl_res.exit_code != 0:
        return [StepResult(level="error", message="TypeWhisper: download failed")]

    # Mount
    _mount_cmd = (
        f"hdiutil attach {_TW_DMG_PATH!r} -nobrowse -noautoopen 2>/dev/null"
        " | grep -oE '/Volumes/.*' | tail -1"
    )
    mount_res = runner.run(("sh", "-c", _mount_cmd))
    tw_mount = mount_res.stdout.strip()
    if not tw_mount:
        return [StepResult(level="error", message="TypeWhisper: DMG mount failed")]

    # Copy
    copy_res = runner.run(("sh", "-c", f"cp -R {tw_mount!r}/TypeWhisper.app /Applications/"))

    # Detach (best-effort)
    runner.run(("sh", "-c", f"hdiutil detach {tw_mount!r} -quiet 2>/dev/null || true"))

    # Cleanup
    runner.run(("sh", "-c", f"rm -f {_TW_DMG_PATH!r}"))

    if copy_res.exit_code != 0:
        return [StepResult(level="error", message="TypeWhisper: copy to /Applications failed")]

    return [StepResult(level="success", message="TypeWhisper installed")]


def install_npm_globals(
    manifest: PackageManifest,
    runner: ProcessRunner,
    *,
    flags_on: set[str],
) -> list[StepResult]:
    """Install npm global packages declared in [[npm_package]] sections.

    Idempotency guard: skips each package if `which <name>` succeeds.
    Flag-gated: packages with a flag are skipped when that flag is not in flags_on.
    """
    results: list[StepResult] = []
    for pkg in manifest.npm_packages:
        if not _flag_active(pkg.flag, flags_on):
            continue
        check = runner.run(("sh", "-c", f"command -v {pkg.name}"))
        if check.stdout.strip() or check.exit_code == 0:
            results.append(
                StepResult(level="info", message=f"{pkg.name} already installed — skipping")
            )
            continue
        res = runner.run(("npm", "install", "-g", pkg.name))
        if res.exit_code == 0:
            results.append(StepResult(level="success", message=f"npm install -g {pkg.name}"))
        else:
            results.append(StepResult(level="error", message=f"npm install -g {pkg.name} failed"))
    return results
