"""bake_rules — port of agents/shared/bake-rules.sh.

Strips YAML frontmatter from each ``.ai/rules/process/*.mdc`` file and emits
each as a ``## <name>`` section, joined by ``---`` separators.

Used by vendor setup scripts that write a single global instruction file
(e.g. codex AGENTS.md, gemini GEMINI.md) instead of a rules directory.
"""

from __future__ import annotations

from pathlib import Path


def _strip_frontmatter(text: str) -> str:
    """Strip YAML frontmatter (everything up to and including the 2nd ``---`` line).

    Faithful to the awk in bake-rules.sh: ``awk '/^---$/{c++;next} c>=2{print}'``.
    Does NOT strip leading newlines from the body — awk prints whatever follows.
    """
    lines = text.splitlines(keepends=True)
    dashes_seen = 0
    for i, line in enumerate(lines):
        if line.rstrip("\n\r") == "---":
            dashes_seen += 1
            if dashes_seen == 2:
                return "".join(lines[i + 1 :])
    # No frontmatter found — return as-is
    return text


def bake_rules(dotfiles_dir: Path) -> str:
    """Bake all process rules into a single Markdown string.

    Matches the exact output shape of ``bake_rules()`` in bake-rules.sh:
    - Preamble header line (``# Universal rules (baked from ...)``)
    - Italicised source note
    - Each rule preceded by ``\\n---\\n\\n## <name>\\n\\n`` (including the first)
    - Rules are sorted alphabetically (glob order)
    """
    rules_dir = dotfiles_dir / ".ai" / "rules" / "process"
    if not rules_dir.is_dir():
        return ""

    rule_files = sorted(rules_dir.glob("*.mdc"))
    if not rule_files:
        return ""

    # Preamble — source shown relative to the repo (no Path.home() in core).
    rel_dir = rules_dir.relative_to(dotfiles_dir)
    preamble = (
        "\n# Universal rules (baked from .ai/rules/process/)\n\n"
        f"_These rules govern process, safety, and coding conventions for all AI coding work."
        f" Source: `{rel_dir}/*.mdc`._"
    )

    parts: list[str] = [preamble]
    for rule in rule_files:
        if not rule.is_file():
            continue
        name = rule.stem
        body = _strip_frontmatter(rule.read_text())
        parts.append(f"## {name}\n\n{body}")

    # Each rule (including the first) is preceded by \n---\n\n
    # preamble + N rules → join everything with \n---\n\n
    return "\n---\n\n".join(parts)
