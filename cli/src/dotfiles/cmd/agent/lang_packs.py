"""Language packs: per-language suppression patterns + tool reference.

`dotfiles agent health` detects a repo's language from marker files and seeds
baselines.json from the matching pack, so the ratchet counts the right things in a
Go/Rust/TS repo, not just Python. Packs are JSON in ai/skills/converge/lang/; the
GENERIC fallback covers an unrecognized repo.
"""

from __future__ import annotations

import json
from pathlib import Path

from dotfiles.cmd.agent.models import LanguagePack

# Multi-language fallback when no marker matches — the original hand-coded set.
GENERIC = LanguagePack(
    language="generic",
    files_glob="**/*",
    suppression_patterns={
        "type-ignore": r"# *type: *ignore|// *@ts-(ignore|expect-error)",
        "lint-disable": r"# *noqa|# *pyright: *ignore|eslint-disable|biome-ignore",
        "allow-attr": r"#\[allow\(",
        # Factored so this isn't a literal that could match its own grep.
        "broad-except": r"except (Exception|BaseException)",
        "any-type": r"dict\[str, *Any\]|: *Any\b|\bas any\b",
        "cast-escape": r"\bcast\(|\.unwrap\(\)",
        "skipped-test": r"@pytest\.mark\.skip|\bit\.skip\b|#\[ignore\]",
        "todo": r"TODO|FIXME|XXX",
        "no-cover": r"# *pragma: *no cover|c8 ignore",
    },
)


def load_packs(lang_dir: Path) -> list[LanguagePack]:
    """Load every <language>.json pack from lang_dir (sorted, deterministic)."""
    if not lang_dir.is_dir():
        return []
    return [LanguagePack(**json.loads(f.read_text())) for f in sorted(lang_dir.glob("*.json"))]


def detect_pack(target: Path, lang_dir: Path) -> LanguagePack:
    """Pick the pack whose marker file is present at the repo root, else GENERIC.

    First match by sorted filename wins; a polyglot repo can override via --glob.
    """
    for pack in load_packs(lang_dir):
        if any((target / marker).exists() for marker in pack.markers):
            return pack
    return GENERIC
