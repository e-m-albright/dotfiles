#!/usr/bin/env bash
# bake_rules — concatenate .ai/rules/process/*.mdc bodies (frontmatter stripped)
# into a single stream. Used by vendor setup scripts that have a single global
# instruction file (codex AGENTS.md) and no separate rules-directory mechanism.
# Claude Code uses ~/.claude/rules/*.md natively; Cursor uses project-level
# .cursor/rules/ via scaffold.sh — neither needs baking.
#
# Usage (sourced):
#   source agents/shared/bake-rules.sh
#   bake_rules "$DOTFILES_DIR" > /path/to/output.md
#
# Or piped:
#   bake_rules "$DOTFILES_DIR" >> ~/.codex/AGENTS.md
#
# Output shape: each rule appears as a "## <name>" section, in alphabetical
# order, with YAML frontmatter stripped from the source.

bake_rules() {
    local dotfiles_dir="${1:-$HOME/dotfiles}"
    local rules_dir="$dotfiles_dir/.ai/rules/process"
    [[ -d "$rules_dir" ]] || return 0

    printf '\n# Universal rules (baked from .ai/rules/process/)\n\n'
    printf '_These rules govern process, safety, and coding conventions for all AI coding work. Source: `%s/*.mdc`._\n' \
        "${rules_dir/$HOME/\~}"

    for rule in "$rules_dir"/*.mdc; do
        [[ -f "$rule" ]] || continue
        local name
        name="$(basename "$rule" .mdc)"
        printf '\n---\n\n## %s\n\n' "$name"
        # Strip YAML frontmatter: print everything after the second `---`
        awk '/^---$/{c++;next} c>=2{print}' "$rule"
    done
}
