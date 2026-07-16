# dotfiles dev tasks. Run `just` for grouped help.

repo := justfile_directory()

set working-directory := 'cli'

# ── Quality ───────────────────────────────────────────────────────────────────

# Format Python sources. `just fmt --check` (or `just fmt check`) verifies only.
[group('quality')]
fmt mode='write':
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{mode}}" in
        write | all) uv run ruff format . ;;
        --check | check) uv run ruff format --check . ;;
        *)
            printf 'fmt: unknown mode %q (try --check, check)\n' "{{mode}}" >&2
            exit 1
            ;;
    esac

# Ruff lint.
[group('quality')]
lint:
    uv run ruff check .

# Pyright typecheck.
[group('quality')]
types:
    uv run pyright

# Vulture dead-code scan.
[group('quality')]
deadcode:
    uv run vulture src .vulture_whitelist.py --min-confidence 80

# Complexipy cognitive complexity gate.
[group('quality')]
complexity:
    uv run complexipy src -mx 9

# ShellCheck every shell script at the pre-commit warning threshold.
[group('quality')]
lint-shell:
    #!/usr/bin/env bash
    set -euo pipefail
    find "{{repo}}" -name '*.sh' -not -path '*/.git/*' -print0 | xargs -0 shellcheck -S warning

# Full static-check + test gate. `just check --fast` (or `check fast`) skips tests — pre-commit.
[group('quality')]
check mode='all':
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{mode}}" in
        all) run_test=1 ;;
        --fast | fast) run_test=0 ;;
        *)
            printf 'check: unknown mode %q (try --fast, fast)\n' "{{mode}}" >&2
            exit 1
            ;;
    esac
    just fmt --check
    just lint
    just types
    just deadcode
    just complexity
    if [[ "$run_test" -eq 1 ]]; then
        just test
    fi

# ── Testing ───────────────────────────────────────────────────────────────────

# Pytest with coverage floor.
[group('testing')]
test:
    uv run pytest --cov=dotfiles --cov-report=term-missing --cov-fail-under=85

# ── Dependencies ──────────────────────────────────────────────────────────────

# pip-audit dependency vulnerabilities.
[group('dependencies')]
audit:
    uv run pip-audit

# ── Cleanup ───────────────────────────────────────────────────────────────────

# Scrub ephemeral files. Default: both. `just scrub --artifacts`, `just scrub --caches`
[group('cleanup')]
scrub mode='all':
    #!/usr/bin/env bash
    set -euo pipefail
    do_artifacts=false
    do_caches=false
    case "{{mode}}" in
        all) do_artifacts=true; do_caches=true ;;
        --artifacts | artifacts) do_artifacts=true ;;
        --caches | caches) do_caches=true ;;
        *)
            printf 'scrub: unknown mode %q (try all, --artifacts, --caches)\n' "{{mode}}" >&2
            exit 1
            ;;
    esac
    if $do_artifacts; then
        rm -rf "{{repo}}/docs/adr" "{{repo}}/docs/specs" "{{repo}}/docs/plans" "{{repo}}/docs/superpowers"
    fi
    if $do_caches; then
        rm -rf "{{repo}}/cli/.complexipy_cache" "{{repo}}/.crush" "{{repo}}/cli/.ruff_cache" "{{repo}}/cli/.pytest_cache"
    fi

# ── Help (default) ────────────────────────────────────────────────────────────

# Grouped recipe list. Run bare `just` or `just help`.
[default]
help:
    #!/usr/bin/env bash
    export JUST_LIST_HEADING=$'\e[1;38;2;242;169;0m dotfiles CLI\e[0m · dev tasks (cwd: cli/)\n'
    exec just --justfile "{{justfile()}}" --list --unsorted
