"""Brew package manifest: models, parser, and install-plan logic.

Reads macos/packages.toml (the source of truth for Homebrew packages) and
provides:
  - Pydantic models for the manifest structure
  - PackageManifest.load(path) to parse the TOML file
  - enabled_packages() to list what should be installed given active flags
  - installed_formulae() / installed_casks() to query the current machine
  - stale_packages() / missing_packages() for install-plan computation
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
