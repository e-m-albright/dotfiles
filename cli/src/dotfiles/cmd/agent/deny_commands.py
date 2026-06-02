"""Canonical 'hard stop' command vocabulary loader.

Single source of truth lives in ``ai/agents/shared/deny-commands.yaml``. The
per-vendor deny lists are hand-authored in each tool's own committed config
(their syntaxes differ and the patterns are security-critical, so we do not
machine-translate them). This module just reads the registry and exposes the
per-surface strings so a drift gate (test_deny_commands_sync.py) can assert each
one literally appears in the matching committed config.

Path is injected; Path.home() MUST NOT appear here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast


def _as_dict(obj: object) -> dict[str, object]:
    return cast("dict[str, object]", obj) if isinstance(obj, dict) else {}


def _as_list(obj: object) -> list[object]:
    return cast("list[object]", obj) if isinstance(obj, list) else []


SURFACES = ("claude", "cursor", "zed", "pi", "gemini")

# Where each surface's deny strings must appear (relative to the dotfiles dir).
SURFACE_FILES: dict[str, str] = {
    "claude": "ai/agents/claude/permissions.json",
    "cursor": "ai/agents/cursor/cli-config.json",
    "zed": "editors/zed/settings.json",
    "pi": "ai/agents/pi/permission-policy.json",
    "gemini": "ai/agents/gemini/settings.json",
}


@dataclass(frozen=True)
class DenyEntry:
    """One canonical danger command and its per-surface representations."""

    id: str
    desc: str
    category: str
    surfaces: dict[str, str]


def deny_yaml_path(dotfiles_dir: Path) -> Path:
    return dotfiles_dir / "ai" / "agents" / "shared" / "deny-commands.yaml"


def load_deny_entries(dotfiles_dir: Path) -> list[DenyEntry]:
    """Parse the canonical registry into a flat list of DenyEntry."""
    import yaml  # pyyaml — lazy import, matches vendors/claude.py

    raw: object = yaml.safe_load(deny_yaml_path(dotfiles_dir).read_text(encoding="utf-8")) or {}
    entries: list[DenyEntry] = []
    for category in _as_list(_as_dict(raw).get("categories")):
        cat = _as_dict(category)
        cat_name = str(cat.get("name", ""))
        for entry_obj in _as_list(cat.get("entries")):
            entry = _as_dict(entry_obj)
            surfaces = {s: str(entry[s]) for s in SURFACES if s in entry}
            entries.append(
                DenyEntry(
                    id=str(entry["id"]),
                    desc=str(entry.get("desc", "")),
                    category=cat_name,
                    surfaces=surfaces,
                )
            )
    return entries


def strings_for_surface(dotfiles_dir: Path, surface: str) -> list[str]:
    """Return every deny string declared for ``surface`` in registry order."""
    return [e.surfaces[surface] for e in load_deny_entries(dotfiles_dir) if surface in e.surfaces]


def _strip_line_comments(text: str) -> str:
    """Drop full-line ``//`` comments so JSONC parses as JSON.

    Only lines whose first non-whitespace is ``//`` are removed, so ``https://``
    inside string values is never touched. Zed's settings.json uses only
    full-line comments; if inline trailing comments are ever added this needs a
    real JSONC parser.
    """
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("//"))


def deny_strings_in_config(dotfiles_dir: Path, surface: str) -> set[str]:
    """Parse a surface's committed config and return its deny strings.

    Membership (not substring) so JSON backslash-escaping is handled correctly:
    a regex ``\\bsudo\\b`` is stored as ``"\\\\bsudo\\\\b"`` on disk but parses
    back to the same logical string the registry holds.
    """
    text = (dotfiles_dir / SURFACE_FILES[surface]).read_text(encoding="utf-8")
    raw = _strip_line_comments(text) if surface == "zed" else text
    data = _as_dict(json.loads(raw))
    if surface == "claude":
        return {str(x) for x in _as_list(data.get("deny"))}
    if surface == "cursor":
        return {str(x) for x in _as_list(_as_dict(data.get("permissions")).get("deny"))}
    if surface == "pi":
        return {
            str(p)
            for rule in _as_list(data.get("denyCommands"))
            for p in _as_list(_as_dict(rule).get("patterns"))
        }
    if surface == "gemini":
        return {str(x) for x in _as_list(_as_dict(data.get("tools")).get("exclude"))}
    if surface == "zed":
        terminal = _as_dict(
            _as_dict(
                _as_dict(_as_dict(data.get("agent")).get("tool_permissions")).get("tools")
            ).get("terminal")
        )
        return {
            str(_as_dict(rule).get("pattern", "")) for rule in _as_list(terminal.get("always_deny"))
        }
    raise ValueError(f"unknown surface: {surface}")
