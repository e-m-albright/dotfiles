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

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.result import StepResult

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
    disabled: bool = False
    reason: str = ""


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
    return {line for line in result.stdout.splitlines() if line.strip()}


def installed_casks(runner: ProcessRunner) -> set[str]:
    """Return the set of casks currently installed via Homebrew."""
    result = runner.run(("brew", "list", "--cask", "-1"))
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
    return {line.rsplit("/", 1)[-1] for line in result.stdout.splitlines() if line.strip()}


def stale_packages(
    manifest: PackageManifest,
    runner: ProcessRunner,
) -> list[str]:
    """Return installed packages that are not declared anywhere in the manifest.

    "Stale" means a top-level (explicitly requested) package installed on this
    machine but not mentioned at all in packages.toml (not even as disabled).
    Transitive dependencies are excluded — see requested_formulae(). A disabled
    package is declared, so it is NOT stale.
    """
    declared = _all_declared_names(manifest)
    # Only consider top-level (requested) formulae — never transitive deps.
    formulae = requested_formulae(runner)
    casks = installed_casks(runner)
    installed = formulae | casks
    # A versioned keg (openssl@3) is not stale when its base name (openssl) is
    # declared — mirrors the alias-aware match in missing_packages.
    stale = sorted(
        name for name in installed if name not in declared and _strip_version(name) not in declared
    )
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
    # Treat a versioned keg (openssl@3) as satisfying its declared base (openssl),
    # so an alias declaration is not re-installed on every run.
    satisfied = installed | {_strip_version(name) for name in installed}
    wanted = enabled_packages(manifest, flags_on=flags_on)
    return [(name, kind) for name, kind in wanted if name not in satisfied]


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


def install_rust(runner: ProcessRunner, *, home: Path) -> list[StepResult]:
    """Install Rust via rustup if not already present.

    Idempotency guard: skips if `rustup` or `cargo` is on PATH.
    Post-install: ensures <home>/.zprofile sources ~/.cargo/env.

    ``home`` must be injected by the caller (never Path.home() inside core) so
    that tests can pass a tmp_path and never touch the real home directory.
    """
    check = runner.run(_RUSTUP_CHECK)
    if check.stdout.strip():
        return [StepResult(level="info", message="Rust already installed — skipping")]

    res = runner.run(_RUSTUP_INSTALL)
    if res.exit_code != 0:
        return [StepResult(level="error", message=f"rustup installer failed: {res.stderr.strip()}")]

    # Idempotent .zprofile patch via pathlib (no runner needed for file I/O)
    zprofile = home / ".zprofile"
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

    # Download. argv form (no shell) so the GitHub-sourced URL is never parsed
    # by a shell — removes the injection footgun of interpolating tw_url into sh -c.
    dl_res = runner.run(("curl", "-fsSL", "-o", _TW_DMG_PATH, tw_url))
    if dl_res.exit_code != 0:
        return [StepResult(level="error", message="TypeWhisper: download failed")]

    # Mount (genuine pipeline → needs a shell; only the constant path is interpolated)
    _mount_cmd = (
        f"hdiutil attach {_TW_DMG_PATH!r} -nobrowse -noautoopen 2>/dev/null"
        " | grep -oE '/Volumes/.*' | tail -1"
    )
    mount_res = runner.run(("sh", "-c", _mount_cmd))
    tw_mount = mount_res.stdout.strip()
    if not tw_mount:
        return [StepResult(level="error", message="TypeWhisper: DMG mount failed")]

    # Copy — argv form (no shell).
    copy_res = runner.run(("cp", "-R", f"{tw_mount}/TypeWhisper.app", "/Applications/"))

    # Detach + cleanup (best-effort; argv, exit code ignored).
    runner.run(("hdiutil", "detach", tw_mount, "-quiet"))
    runner.run(("rm", "-f", _TW_DMG_PATH))

    if copy_res.exit_code != 0:
        return [StepResult(level="error", message="TypeWhisper: copy to /Applications failed")]

    return [StepResult(level="success", message="TypeWhisper installed")]


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
    flags_on: set[str],
) -> list[StepResult]:
    """Install npm global packages declared in [[npm_package]] sections.

    Idempotency guard: skips each package if `which <name>` succeeds.
    Flag-gated: packages with a flag are skipped when that flag is not in flags_on.
    """
    steps = (_install_one_npm(pkg, runner, flags_on=flags_on) for pkg in manifest.npm_packages)
    return [s for s in steps if s is not None]


def _install_one_npm(
    pkg: NpmPackage, runner: ProcessRunner, *, flags_on: set[str]
) -> StepResult | None:
    """Install one npm global, or None if it's disabled/flag-gated. Idempotent."""
    if pkg.disabled or not _flag_active(pkg.flag, flags_on):
        return None
    check = runner.run(("sh", "-c", f"command -v {pkg.name}"))
    if check.stdout.strip() or check.exit_code == 0:
        return StepResult(level="info", message=f"{pkg.name} already installed — skipping")
    res = runner.run(("npm", "install", "-g", pkg.name))
    if res.exit_code == 0:
        return StepResult(level="success", message=f"npm install -g {pkg.name}")
    return StepResult(level="error", message=f"npm install -g {pkg.name} failed")


def upgrade(runner: ProcessRunner) -> list[StepResult]:
    """Update Homebrew and upgrade all installed formulae + casks, then prune caches.

    Homebrew is the only version-pinning surface in this managed setup, so this is
    the one-shot "bring my packages current" convenience.
    """
    results: list[StepResult] = []
    runner.run(("brew", "update"))
    results.append(StepResult(level="success", message="Updated Homebrew index"))
    res = runner.run(("brew", "upgrade"))
    if res.ok:
        results.append(StepResult(level="success", message="Upgraded formulae + casks"))
    else:
        results.append(
            StepResult(level="error", message="brew upgrade failed", details=res.stderr.strip())
        )
    runner.run(("brew", "cleanup", "--prune=30"))
    results.append(StepResult(level="info", message="Pruned caches older than 30 days"))
    return results
