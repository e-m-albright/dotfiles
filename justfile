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
typecheck:
    uv run pyright

# Vulture dead-code scan.
[group('quality')]
deadcode:
    uv run vulture src .vulture_whitelist.py --min-confidence 80

# Complexipy cognitive complexity gate.
[group('quality')]
complexity:
    uv run complexipy src -mx 9

# Parse every tracked shell script, strict-JSON file, and YAML file.
[group('quality')]
validate-files:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{repo}}"
    git ls-files -z '*.sh' | while IFS= read -r -d '' file; do
        bash -n "$file"
    done
    git ls-files -z '*.json' | while IFS= read -r -d '' file; do
        case "$file" in
            .claude/* | editors/*) continue ;; # JSONC/vendor-managed files
        esac
        python3 -m json.tool "$file" >/dev/null
    done
    git ls-files -z '*.yaml' '*.yml' | while IFS= read -r -d '' file; do
        ruby -e 'require "yaml"; YAML.parse_file(ARGV.fetch(0))' "$file"
    done

# ShellCheck every shell script at the pre-commit warning threshold.
[group('quality')]
lint-shell:
    #!/usr/bin/env bash
    set -euo pipefail
    # Only tracked scripts — never vendored third-party .sh under .venv/node_modules.
    cd "{{repo}}" && git ls-files -z '*.sh' | xargs -0 shellcheck -S warning

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
    just typecheck
    just deadcode
    just complexity
    if [[ "$run_test" -eq 1 ]]; then
        just test
    fi

# Public-repo privacy sweep: no absolute home paths or private-project names in
# tracked files. Names come from a machine-local denylist so they never enter
# the repo; test fixtures use /home/dev so the path grep can stay strict.
[group('quality')]
privacy-sweep:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{repo}}"
    status=0
    if git grep -nI -E '/Users/[A-Za-z]' -- ':(exclude)justfile'; then
        echo "privacy-sweep: absolute home path in tracked files (use ~ or \$HOME)" >&2
        status=1
    fi
    terms="$HOME/.config/dotfiles/private-terms.txt"
    if [[ -f "$terms" ]]; then
        while IFS= read -r term; do
            [[ -z "$term" || "$term" == \#* ]] && continue
            if git grep -niI -F "$term" >/dev/null; then
                echo "privacy-sweep: private term found (see denylist): matches for a listed term" >&2
                git grep -niI -F "$term" | head -5
                status=1
            fi
        done < "$terms"
    fi
    exit "$status"

# Everything AGENTS.md lists as the verification set, in one command.
[group('quality')]
verify:
    just validate-files
    just check
    just lint-shell
    just audit
    just privacy-sweep

# ── Testing ───────────────────────────────────────────────────────────────────

# Pytest with coverage floor.
[group('testing')]
test:
    uv run pytest --cov=dotfiles --cov-report=term-missing --cov-fail-under=95

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
        rm -rf "{{repo}}/.complexipy_cache" "{{repo}}/.ruff_cache" "{{repo}}/.pytest_cache" "{{repo}}/cli/coverage.json" "{{repo}}/cli/snapshot_report.html"
    fi

# ── Help (default) ────────────────────────────────────────────────────────────

# Grouped recipe list. Run bare `just` or `just help`.
[default]
help:
    #!/usr/bin/env bash
    export JUST_LIST_HEADING=$'\e[1;38;2;242;169;0m dotfiles CLI\e[0m · dev tasks (cwd: cli/)\n'
    exec just --justfile "{{justfile()}}" --list --unsorted
