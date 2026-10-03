"""Host entrypoints must resolve their inputs after directory moves."""

import re
from pathlib import Path

ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "AGENTS.md").is_file()
)


def test_installer_and_shell_reference_existing_inputs() -> None:
    for source in (
        ROOT / "scripts/install.sh",
        ROOT / "config/zsh/.zshrc",
        ROOT / "bin/dotfiles",
    ):
        text = source.read_text()
        paths = re.findall(
            r'(?:\$DOTFILES_DIR|\$\{DOTFILES_DIR[^}]*\})/([^"\s$]+)', text
        )
        assert paths, source
        for relative in paths:
            assert (ROOT / relative).exists(), (source, relative)


def test_package_manifest_has_one_canonical_home() -> None:
    assert list(ROOT.glob("*/packages.toml")) == [ROOT / "config/packages.toml"]


def test_executable_sources_do_not_reference_retired_homes() -> None:
    roots = [ROOT / name for name in ("bin", "scripts", "config", "cli/src")]
    paths = [ROOT / "cli/.vulture_whitelist.py", ROOT / "install.sh"]
    paths.extend(
        path
        for root in roots
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
    retired = (
        "dotfiles.cmd.",
        "dotfiles.adapters.ports",
        "macos/packages.toml",
        "macos/print_utils.sh",
        "macos/link_utils.sh",
        "macos/configure-omlx.sh",
        "shell/.zshrc",
        "shell/completions",
        "terminal/ghostty.config",
        "editors/zed/",
    )
    for path in paths:
        text = path.read_text()
        assert not {name for name in retired if name in text}, path
