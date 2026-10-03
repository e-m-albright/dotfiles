"""Package declarations, validation, and profile selection."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    """Full parsed contents of config/packages.toml."""

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


def flag_active(flag: FeatureFlag | None, flags_on: set[FeatureFlag]) -> bool:
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
        if not pkg.disabled and flag_active(pkg.flag, flags_on)
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
        if not flag_active(section.flag, flags_on):
            continue
        result.extend(_section_enabled_packages(section, flags_on))
    return result


def declared_names(manifest: PackageManifest) -> set[str]:
    """All package names declared in the manifest, enabled OR disabled."""
    return {pkg.name for section in manifest.sections for pkg in section.packages}
