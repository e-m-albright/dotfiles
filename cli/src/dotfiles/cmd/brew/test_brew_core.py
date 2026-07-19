"""Tests for Brew manifest models, parsing, and install-plan logic."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from dotfiles.cmd.brew.service import (
    BrewInventoryError,
    PackageManifest,
    enabled_packages,
    installed_casks,
    installed_formulae,
    missing_packages,
    requested_formulae,
    stale_packages,
)
from dotfiles.testing.fakes import FakeProcessRunner

# ---------------------------------------------------------------------------
# Minimal TOML fixture helpers
# ---------------------------------------------------------------------------

MINIMAL_TOML = """\
[flags]
ai = true
productivity = true
social = true

[taps]
list = ["some/tap"]

[[section]]
name = "Core CLI"
kind = "formula"
packages = [
  { name = "git", note = "Version control" },
  { name = "curl", note = "HTTP client" },
  { name = "ffmpeg", note = "Video", disabled = true, reason = "too big" },
]

[[section]]
name = "Productivity"
kind = "cask"
flag = "productivity"
packages = [
  { name = "obsidian", note = "Notes" },
  { name = "warp", note = "AI terminal", disabled = true, reason = "not needed" },
]

[[section]]
name = "AI Tools"
kind = "auto"
flag = "ai"
packages = [
  { name = "claude", note = "Claude desktop" },
  { name = "codex", note = "OpenAI Codex" },
]

[special.rust]
method = "rustup"
url = "https://sh.rustup.rs"
args = ["-y"]

[special.typewhisper]
method = "github_dmg"
flag = "productivity"
repo = "TypeWhisper/typewhisper-mac"

[[npm_package]]
name = "wrangler"
note = "Cloudflare Workers CLI"

[[npm_package]]
name = "agent-browser"
flag = "ai"
note = "Browser automation"
"""


def make_toml(tmp_path: Path, content: str = MINIMAL_TOML) -> Path:
    p = tmp_path / "packages.toml"
    p.write_text(content)
    return p


# ---------------------------------------------------------------------------
# PackageManifest.load — structural tests
# ---------------------------------------------------------------------------


def test_load_flags(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    assert manifest.flags.ai is True
    assert manifest.flags.productivity is True
    assert manifest.flags.social is True


def test_load_taps(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    assert manifest.taps.items == ["some/tap"]


def test_load_sections_count(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    assert len(manifest.sections) == 3


def test_load_section_packages(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    core = manifest.sections[0]
    assert core.name == "Core CLI"
    assert core.kind == "formula"
    assert core.flag is None
    names = [p.name for p in core.packages]
    assert names == ["git", "curl", "ffmpeg"]


def test_load_disabled_package(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    ffmpeg = manifest.sections[0].packages[2]
    assert ffmpeg.name == "ffmpeg"
    assert ffmpeg.disabled is True
    assert ffmpeg.reason == "too big"


def test_load_rejects_disabled_package_without_reason(tmp_path: Path) -> None:
    content = MINIMAL_TOML.replace(', reason = "too big"', "")
    with pytest.raises(ValidationError, match="disabled package 'ffmpeg' requires a reason"):
        PackageManifest.load(make_toml(tmp_path, content))


def test_load_section_flag(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    prod = manifest.sections[1]
    assert prod.flag == "productivity"


def test_load_specials(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    assert "rust" in manifest.specials
    assert manifest.specials["rust"].method == "rustup"
    assert "typewhisper" in manifest.specials
    assert manifest.specials["typewhisper"].flag == "productivity"


def test_load_npm_packages(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    assert len(manifest.npm_packages) == 2
    names = [n.name for n in manifest.npm_packages]
    assert "wrangler" in names
    assert "agent-browser" in names


def test_load_npm_package_flag(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    ab = next(n for n in manifest.npm_packages if n.name == "agent-browser")
    assert ab.flag == "ai"


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        PackageManifest.load(tmp_path / "nonexistent.toml")


# ---------------------------------------------------------------------------
# enabled_packages — flag gating + disabled filtering
# ---------------------------------------------------------------------------


def test_enabled_all_flags_on(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    enabled = enabled_packages(manifest, flags_on={"ai", "productivity", "social"})
    names = [n for n, _ in enabled]
    # Active packages
    assert "git" in names
    assert "curl" in names
    assert "obsidian" in names
    assert "claude" in names
    assert "codex" in names
    # Disabled must be excluded
    assert "ffmpeg" not in names
    assert "warp" not in names


def test_enabled_productivity_off(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    enabled = enabled_packages(manifest, flags_on={"ai", "social"})
    names = [n for n, _ in enabled]
    assert "obsidian" not in names
    assert "git" in names
    assert "claude" in names


def test_enabled_ai_off(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    enabled = enabled_packages(manifest, flags_on={"productivity", "social"})
    names = [n for n, _ in enabled]
    assert "claude" not in names
    assert "codex" not in names
    assert "git" in names
    assert "obsidian" in names


def test_enabled_no_flags(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    enabled = enabled_packages(manifest, flags_on=set())
    names = [n for n, _ in enabled]
    # Only packages with no section flag and not disabled
    assert "git" in names
    assert "curl" in names
    assert "obsidian" not in names
    assert "claude" not in names


def test_enabled_preserves_kind(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    enabled = enabled_packages(manifest, flags_on={"ai", "productivity", "social"})
    by_name = dict(enabled)
    assert by_name["git"] == "formula"
    assert by_name["obsidian"] == "cask"
    assert by_name["claude"] == "auto"


# ---------------------------------------------------------------------------
# Package-level flag (flag on individual package, not just section)
# ---------------------------------------------------------------------------

PACKAGE_FLAG_TOML = """\
[flags]
ai = true

[taps]
list = []

[[section]]
name = "Mixed"
kind = "formula"
packages = [
  { name = "always-on",   note = "" },
  { name = "ai-only",     note = "", flag = "ai" },
  { name = "social-only", note = "", flag = "social" },
]
"""


def test_package_level_flag_respected(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path, PACKAGE_FLAG_TOML))
    enabled = enabled_packages(manifest, flags_on={"ai"})
    names = [n for n, _ in enabled]
    assert "always-on" in names
    assert "ai-only" in names
    assert "social-only" not in names


def test_manifest_rejects_unknown_feature_flags(tmp_path: Path) -> None:
    content = PACKAGE_FLAG_TOML.replace('flag = "ai"', 'flag = "typo"')
    with pytest.raises(ValidationError):
        PackageManifest.load(make_toml(tmp_path, content))


# ---------------------------------------------------------------------------
# Real packages.toml smoke test
# ---------------------------------------------------------------------------


def test_load_real_manifest() -> None:
    """packages.toml exists and parses without error."""
    real_path = Path(__file__).resolve().parents[5] / "macos" / "packages.toml"
    if not real_path.exists():
        pytest.skip("macos/packages.toml not found")
    manifest = PackageManifest.load(real_path)
    assert len(manifest.sections) >= 10
    # Key packages present
    all_names = {p.name for s in manifest.sections for p in s.packages}
    assert "git" in all_names
    assert "ghostty" in all_names
    assert "claude" in all_names


# ---------------------------------------------------------------------------
# installed_formulae / installed_casks
# ---------------------------------------------------------------------------


def test_installed_formulae_parses_output() -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("brew", "list", "--formula", "-1"),
        stdout="git\ncurl\njq\n",
    )
    assert installed_formulae(runner) == {"git", "curl", "jq"}


def test_installed_formulae_empty() -> None:
    runner = FakeProcessRunner()
    runner.script(("brew", "list", "--formula", "-1"), stdout="")
    assert installed_formulae(runner) == set()


@pytest.mark.parametrize(
    ("command", "inventory"),
    [
        (("brew", "list", "--formula", "-1"), installed_formulae),
        (("brew", "list", "--cask", "-1"), installed_casks),
        (("brew", "leaves", "--installed-on-request"), requested_formulae),
    ],
)
def test_inventory_failure_is_not_an_empty_machine(command, inventory) -> None:
    runner = FakeProcessRunner()
    runner.script(command, exit_code=1, stderr="Homebrew unavailable")

    with pytest.raises(BrewInventoryError, match="Homebrew unavailable"):
        inventory(runner)


def test_installed_casks_parses_output() -> None:
    runner = FakeProcessRunner()
    runner.script(
        ("brew", "list", "--cask", "-1"),
        stdout="obsidian\nghostty\n",
    )
    assert installed_casks(runner) == {"obsidian", "ghostty"}


def test_requested_formulae_strips_tap_prefix() -> None:
    """brew leaves yields tap-qualified names; declared-matching needs short names."""
    runner = FakeProcessRunner()
    runner.script(
        ("brew", "leaves", "--installed-on-request"),
        stdout="git\nariga/tap/atlas\ninfisical/get-cli/infisical\n",
    )
    assert requested_formulae(runner) == {"git", "atlas", "infisical"}


# ---------------------------------------------------------------------------
# stale_packages
# ---------------------------------------------------------------------------


def test_stale_packages_installed_not_declared(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    runner = FakeProcessRunner()
    runner.script(
        ("brew", "leaves", "--installed-on-request"),
        stdout="git\ncurl\nsome-random-tool\n",
    )
    runner.script(("brew", "list", "--cask", "-1"), stdout="")
    stale = stale_packages(manifest, runner)
    assert "some-random-tool" in stale
    assert "git" not in stale
    assert "curl" not in stale


def test_stale_disabled_not_stale(tmp_path: Path) -> None:
    """Disabled packages are declared — they must NOT appear as stale."""
    manifest = PackageManifest.load(make_toml(tmp_path))
    runner = FakeProcessRunner()
    # ffmpeg is disabled in our fixture TOML but IS declared
    runner.script(
        ("brew", "leaves", "--installed-on-request"),
        stdout="ffmpeg\n",
    )
    runner.script(("brew", "list", "--cask", "-1"), stdout="")
    stale = stale_packages(manifest, runner)
    assert "ffmpeg" not in stale


def test_stale_returns_sorted(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    runner = FakeProcessRunner()
    runner.script(
        ("brew", "leaves", "--installed-on-request"),
        stdout="zzz-tool\naaa-tool\n",
    )
    runner.script(("brew", "list", "--cask", "-1"), stdout="")
    stale = stale_packages(manifest, runner)
    assert stale == sorted(stale)


def test_stale_empty_when_nothing_extra(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    runner = FakeProcessRunner()
    runner.script(("brew", "leaves", "--installed-on-request"), stdout="git\ncurl\n")
    runner.script(("brew", "list", "--cask", "-1"), stdout="obsidian\n")
    stale = stale_packages(manifest, runner)
    assert stale == []


# ---------------------------------------------------------------------------
# missing_packages
# ---------------------------------------------------------------------------


def test_missing_packages_basic(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    runner = FakeProcessRunner()
    runner.script(("brew", "list", "--formula", "-1"), stdout="git\n")
    runner.script(("brew", "list", "--cask", "-1"), stdout="")
    missing = missing_packages(manifest, runner, flags_on={"ai", "productivity", "social"})
    names = [n for n, _ in missing]
    # curl is enabled and not installed
    assert "curl" in names
    # git is installed — must not appear
    assert "git" not in names
    # disabled ffmpeg must not appear
    assert "ffmpeg" not in names


def test_missing_respects_flag_gating(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    runner = FakeProcessRunner()
    runner.script(("brew", "list", "--formula", "-1"), stdout="")
    runner.script(("brew", "list", "--cask", "-1"), stdout="")
    # ai OFF → claude/codex must not appear
    missing = missing_packages(manifest, runner, flags_on={"productivity", "social"})
    names = [n for n, _ in missing]
    assert "claude" not in names
    assert "codex" not in names
    assert "obsidian" in names


def test_missing_empty_when_all_installed(tmp_path: Path) -> None:
    manifest = PackageManifest.load(make_toml(tmp_path))
    runner = FakeProcessRunner()
    # Install everything that enabled_packages would return
    enabled = enabled_packages(manifest, flags_on={"ai", "productivity", "social"})
    installed_str = "\n".join(n for n, _ in enabled)
    runner.script(("brew", "list", "--formula", "-1"), stdout=installed_str)
    runner.script(("brew", "list", "--cask", "-1"), stdout=installed_str)
    missing = missing_packages(manifest, runner, flags_on={"ai", "productivity", "social"})
    assert missing == []


# ---------------------------------------------------------------------------
# Version-keg alias matching (openssl declared vs openssl@3 installed)
# ---------------------------------------------------------------------------

_ALIAS_TOML = """\
[taps]
items = []

[[section]]
name = "Core CLI"
kind = "formula"
packages = [
  { name = "openssl", note = "TLS" },
  { name = "git", note = "VCS" },
]
"""


def test_missing_ignores_versioned_keg_of_declared_alias(tmp_path: Path) -> None:
    """A declared alias (openssl) is satisfied by its versioned keg (openssl@3)."""
    manifest = PackageManifest.load(make_toml(tmp_path, _ALIAS_TOML))
    runner = FakeProcessRunner()
    runner.script(("brew", "list", "--formula", "-1"), stdout="openssl@3\ngit\n")
    runner.script(("brew", "list", "--cask", "-1"), stdout="")
    missing = missing_packages(manifest, runner, flags_on=set())
    names = [n for n, _ in missing]
    # openssl@3 satisfies the declared `openssl` — must not be re-installed.
    assert "openssl" not in names


def test_stale_ignores_versioned_keg_of_declared_alias(tmp_path: Path) -> None:
    """An installed versioned keg (openssl@3) is not stale when its base is declared."""
    manifest = PackageManifest.load(make_toml(tmp_path, _ALIAS_TOML))
    runner = FakeProcessRunner()
    runner.script(("brew", "list", "--formula", "-1"), stdout="openssl@3\ngit\n")
    runner.script(("brew", "list", "--cask", "-1"), stdout="")
    stale = stale_packages(manifest, runner)
    assert "openssl@3" not in stale
