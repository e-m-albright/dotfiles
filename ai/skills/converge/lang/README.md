# Language packs

Per-language config for the code-health ratchet, so `dotfiles agent health` seeds
the *right* suppression patterns and file glob for a repo's language — a Go or Rust
repo gets Go/Rust patterns, not the Python-flavoured defaults. This is what makes
"any repo" true rather than "any repo we hand-coded for".

`dotfiles agent health` detects the language from a pack's **marker files** (e.g.
`Cargo.toml` → rust) and seeds `docs/health/<scope>/baselines.json` from the matching
pack. No match → the **generic** fallback (`lang_packs.GENERIC`). Override detection
with `--glob` / `--run-from`.

## Pack schema (`<language>.json`)

| Field | Purpose |
|---|---|
| `language` | the pack's name (recorded in baselines.json) |
| `markers` | files whose presence at the repo root selects this pack |
| `files_glob` | the pathspec the ratchet counts over (`:(glob)`-expanded) |
| `run_from` | dir the glob is relative to |
| `suppression_patterns` | family → extended-regex; the ratchet recounts these (test files excluded) |
| `tools` | reference only — the canonical fmt/lint/types/test/coverage/complexity/mutation/audit command per language (informs the human + the findings ledger, not the ratchet) |

## Adding a language

Drop a `<language>.json` here following the schema, then `dotfiles agent health` in
a repo of that language. Keep `suppression_patterns` factored so a pattern's literal
form can't match its own grep (e.g. `except (Exception|BaseException)`, not the bare
alternation). Per-language taste (pick/avoid, idioms) lives in `docs/stacks/`; this is
just the gate wiring.
