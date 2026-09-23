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


def test_pi_is_an_enabled_pinned_ai_package() -> None:
    manifest = PackageManifest.load(MANIFEST)
    pi = next(
        package
        for package in manifest.npm_packages
        if package.name == "@earendil-works/pi-coding-agent"
    )
    assert not pi.disabled
    assert pi.flag == "ai"
    assert pi.version == "0.86.1"


def test_work_profile_is_the_exact_approved_allowlist() -> None:
    work = PackageManifest.load(MANIFEST).profiles["work"]
    assert work.formulae == [
        "git",
        "git-lfs",
        "git-delta",
        "gh",
        "jq",
        "yq",
        "ripgrep",
        "fd",
        "fzf",
        "bat",
        "zoxide",
        "just",
        "shellcheck",
        "lefthook",
        "gitleaks",
        "fnm",
        "uv",
        "deno",
        "awscli",
        "tenv",
    ]
    assert work.casks == [
        "rectangle",
        "flycut",
        "ghostty",
        "caffeine",
        "flux-app",
        "typewhisper",
        "zed",
        "spotify",
        "claude-code",
        "orbstack",
    ]
    assert work.taps == []
    assert work.specials == []
    assert work.npm_packages == ["@earendil-works/pi-coding-agent"]


def test_disabled_entries_carry_dated_reasons() -> None:
    manifest = PackageManifest.load(MANIFEST)
    # The model validators enforce this on load; assert on real data anyway so
    # the invariant's coverage is visible, not incidental.
    for section in manifest.sections:
        for package in section.packages:
            if package.disabled:
                assert package.reason.strip(), package.name


def test_granola_is_retired() -> None:
    manifest = PackageManifest.load(MANIFEST)
    granola = next(
        package
        for section in manifest.sections
        for package in section.packages
        if package.name == "granola"
    )
    assert granola.disabled
    assert "retired" in granola.reason.lower()


def test_lima_is_retired() -> None:
    manifest = PackageManifest.load(MANIFEST)
    lima = next(
        package
        for section in manifest.sections
        for package in section.packages
        if package.name == "lima"
    )
    assert lima.disabled
    assert "native" in lima.reason.lower()
