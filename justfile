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

# ShellCheck every shell script (blocking). The shell layer's gate — same -S
# warning bar the pre-commit hook uses, run over the whole tree for pre-push/CI.
[group('quality')]
lint-shell:
    #!/usr/bin/env bash
    set -euo pipefail
    find "{{repo}}" -name '*.sh' -not -path '*/.git/*' -print0 | xargs -0 shellcheck -S warning

# Code-health ratchet for the cli scope. `just ratchet --update` lowers ceilings to actuals.
# Runs from cli/ (the baseline's run_from); the monotonic guard lives in the script.
[group('quality')]
ratchet *args:
    bash {{repo}}/ai/skills/converge/scripts/ratchet-check.sh {{repo}}/docs/health/cli/baselines.json {{args}}

# Performance-budget ratchet (manual/nightly — benchmarks are slow + noisy, NOT in `check`).
# `just perf --update` re-baselines to current means (lower only) on this machine.
[group('quality')]
perf *args:
    bash {{repo}}/ai/skills/converge/scripts/perf-check.sh {{repo}}/docs/health/cli/perf-baselines.json {{args}}

# Validate skill/agent markdown frontmatter + body. Catches the silent
# frontmatter-drop trap: `npx skills` discards a skill with invalid YAML, so a
# malformed skill deploys as simply *gone*. Run at pre-commit + CI.
[group('quality')]
lint-agents:
    uv run dotfiles agent lint

# Mutation testing — the test-QUALITY reliability metric (do the tests catch an
# injected bug, not just execute the line?). Slow: one suite run per mutant, so
# manual/nightly and scoped via [tool.mutmut] config or mutant names. uv --with
# means nothing to install. `just mutation` — the Reliability pillar's quality floor.
[group('quality')]
mutation *args:
    uv run --with mutmut mutmut run {{args}}

# Adversarial assessment — route the work past an INDEPENDENT model (default
# Claude Fable 5) acting as a skeptical principal engineer, read-only, to surface
# blind spots. The structural counter to sycophancy. Findings are claims to
# VERIFY, not gospel. Paid + opt-in. `just assess <focus>` or bare for the repo.
[group('quality')]
assess *args:
    bash {{repo}}/ai/skills/adversarial-assessor/scripts/assess.sh {{args}}

# Voice gate (deterministic half): scan prose for banned LLM/marketing slop.
# Delta-scoped — staged *.md by default, or the files passed (commit-msg passes
# its message file). Excludes the doctrine files that quote the phrases. The
# semantic half — sycophancy, hedging — is the stochastic ai/audits/voice.md.
[group('quality')]
lint-prose *files:
    #!/usr/bin/env bash
    set -euo pipefail
    list="{{repo}}/ai/agents/shared/slop-phrases.txt"
    excludes='slop-phrases\.txt|rules\.md|shared-rules\.mdc|CANON\.md|how-we-build\.md|engineering-philosophy\.md|audits/voice\.md'
    files="{{files}}"
    [ -n "$files" ] || files=$(git diff --cached --name-only --diff-filter=ACM -- '*.md' || true)
    [ -n "$files" ] || { echo "voice: no prose to check"; exit 0; }
    found=0
    for f in $files; do
        [ -f "$f" ] || continue
        printf '%s\n' "$f" | grep -qE "$excludes" && continue
        while IFS= read -r phrase; do
            case "$phrase" in ''|'#'*) continue ;; esac
            if grep -inF -- "$phrase" "$f" >/dev/null 2>&1; then
                grep -inF -- "$phrase" "$f" | sed "s|^|$f:|"
                found=1
            fi
        done < "$list"
    done
    # Em-dash (U+2014) is an LLM tell. ADVISORY (warn, never block): *.md is exempt
    # (docs/specs/ADRs use it legitimately); code + commit messages are flagged.
    # Promote to blocking after a stability cycle (PREVIEW over BLOCK; gates 5).
    for f in $files; do
        [ -f "$f" ] || continue
        case "$f" in *.md) continue ;; esac
        if grep -q '—' "$f" 2>/dev/null; then
            grep -n '—' "$f" | sed "s|^|$f (em-dash, advisory): |"
        fi
    done
    if [ "$found" -eq 1 ]; then
        echo "voice: banned slop phrase(s) above — rephrase (see ai/agents/shared/slop-phrases.txt)" >&2
        exit 1
    fi
    echo "voice OK — no slop."

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
    just ratchet
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
    export JUST_LIST_HEADING=$'\e[1;34m dotfiles CLI\e[0m — dev tasks (cwd: cli/)\n'
    exec just --justfile "{{justfile()}}" --list --unsorted
