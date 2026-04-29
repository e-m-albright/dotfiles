# Baselines Scaffold

Code-health ratchet system lifted from Ophira and made portable. Counts of anti-patterns and per-file line ceilings live in `baselines.json`. Pre-commit hook fails if any metric exceeds its ceiling. Improvements are locked in via `--auto-ratchet`.

## What this scaffold deploys

```
baselines.json                      # ceilings (you edit; ratchet edits)
scripts/check_baselines.py          # validator + auto-ratchet
lefthook.baselines.yml              # fragment to merge into your lefthook.yml
```

## Initial setup

```bash
# 1. Run the checker against the current codebase to populate baselines.
python3 scripts/check_baselines.py --auto-ratchet

# 2. Wire the lefthook fragment.
cat lefthook.baselines.yml >> lefthook.yml
lefthook install
```

## Workflow

- **Day-to-day**: every commit runs the ratchet; you can't sneak a new `# type: ignore` past it.
- **After a cleanup PR**: run `python3 scripts/check_baselines.py --auto-ratchet` to lock the new (lower) numbers in.
- **Adding a new metric**: edit `METRICS` in `check_baselines.py` and add a ceiling to `baselines.json`. The script's structure (pattern + paths + globs) lets you add metrics for any language.
- **Adding a file ceiling**: when refactoring a large file, add an entry under `file_ceilings` to lock the win.

## Suggested starting metrics

The default `METRICS` covers `todo_total`, `type_ignore_total`, `as_any_total`. Add more as your stack matures:

| Stack | Metric | Pattern |
|-------|--------|---------|
| Rust | `rust_allow_total` | `#\[allow(` |
| Rust | `unwrap_in_src` | `\.unwrap\(\)` (excluding tests) |
| Python | `noqa_total` | `# noqa` |
| Python | `dict_str_any` | `dict\[str, Any\]` |
| Web | `inline_styles` | `style="` |
| Web | `ts_ignore_total` | `@ts-` |

See `docs/engineering-philosophy.md` for the philosophy behind suppressions ratcheting downward (Principle 10).
