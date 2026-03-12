# Dotfiles — Claude Code Project Instructions

Read `AGENTS.md` for repo overview and conventions.
Read `.ai/rules/process/*.mdc` for universal process rules (these are the canonical source — they get scaffolded into other projects).

## This Repo

This is a dotfiles and dev environment repo, not a typical application. Key differences:

- **Primary language is Bash** — all scripts use `set -euo pipefail` (or `set -eo pipefail` when arrays may be unset)
- **Print system** — use functions from `macos/print_utils.sh` (print_success, print_info, print_warn, print_action, print_step, print_skip, etc.). Never use raw `echo` or bare `printf` for user-facing output.
- **Idempotent** — every script must be safe to re-run. Check before creating, skip if present, don't error on existing state.
- **The `dotfiles` command** (`bin/dotfiles`) is the user-facing CLI. New features should be subcommands here, not standalone scripts.

## Key Invariants

- `brew.sh` package lists are the source of truth for what's installed. `bin/dotfiles doctor` and `bin/dotfiles stale` must stay in sync with these lists.
- `README.md` documents user-facing features. When adding/removing/renaming commands, packages, or config, update the README in the same commit.
- `.ai/rules/` is the canonical rule library. `prompts/scaffold.sh` copies these into projects. Rules are not symlinked.
- `prompts/guides/skills/*.md` are implementation references that complement `.ai/rules/`. They should stay consistent with each other.

## Common Pitfalls

- `printf "%s"` does not interpret escape codes — use `%b` when the argument contains `\033[` color sequences (see `print_todo`).
- `ssh -T git@github.com` exits with code 1 even on success — capture output with `|| true` before grepping.
- `set -eo pipefail` kills pipelines where the left side exits non-zero — capture to a variable first if needed.
