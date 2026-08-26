"""The real packages.toml must satisfy the manifest model's invariants.

Loading through PackageManifest exercises TOML well-formedness and the
tombstone rule (disabled entries carry a dated reason), so a malformed edit
fails `just check` instead of surfacing on the next `dotfiles brew install`.
"""

from pathlib import Path

from dotfiles.cmd.brew.service import PackageManifest

MANIFEST = Path(__file__).parent / "packages.toml"


def test_packages_toml_loads_through_model() -> None:
    manifest = PackageManifest.load(MANIFEST)
    assert manifest.sections, "packages.toml parsed to zero sections"


def test_disabled_entries_carry_dated_reasons() -> None:
    manifest = PackageManifest.load(MANIFEST)
    # The model validators enforce this on load; assert on real data anyway so
    # the invariant's coverage is visible, not incidental.
    for section in manifest.sections:
        for package in section.packages:
            if package.disabled:
                assert package.reason.strip(), package.name
