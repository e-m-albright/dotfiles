# Agent Rules Sync

Make project-level `.ai/rules/*.mdc` files reliably load in every agent harness without "go read this path" indirection (which Claude Code in particular ignores).

## What it solves

You wrote a perfectly good `.ai/rules/python.mdc` for your project. You added a directive in `AGENTS.md` saying "Read all `.ai/rules/*.mdc` files for project conventions." A Claude Code session in your repo silently ignores it. Cursor reads them. Codex reads `AGENTS.md` but not the rules. The shim doesn't work.

The fix is to materialize rules into each harness's native loader path:

| Harness | Native loader path | How rules arrive |
|---------|-------------------|------------------|
| Cursor | `.cursor/rules/*.mdc` (with frontmatter `alwaysApply` / `globs`) | Per-file symlinks → `.ai/rules/*.mdc` |
| Claude Code | `AGENTS.md` | All rule bodies inlined between fenced markers |
| Codex CLI | `AGENTS.md` (native) | All rule bodies inlined |
| Gemini CLI | `GEMINI.md` → symlinked to `AGENTS.md` | All rule bodies inlined |

`sync-agent-rules.sh` keeps both targets current. Pre-commit drift guard refuses stale renders.

## What gets installed

- `scripts/sync-agent-rules.sh` — the sync + drift-check script
- `lefthook.agent-rules.yml` — pre-commit fragment (merge into your `lefthook.yml`)

## After install

1. Author rules in `.ai/rules/*.mdc` with optional frontmatter (`description`, `globs`, `alwaysApply`).
2. Add the fenced markers to `AGENTS.md` wherever you want the rules to land:
   ```markdown
   <!-- BEGIN: project rules (auto-generated from .ai/rules/) -->
   <!-- END: project rules -->
   ```
3. Run `./scripts/sync-agent-rules.sh` once. After that, the pre-commit hook keeps it current.
4. Wire the lefthook fragment into your `lefthook.yml` (or your project's hook runner).

## Optional: just recipe

If your project uses `just`, add:

```just
# Sync .ai/rules/*.mdc → .cursor/rules + render into AGENTS.md
agents:
    ./scripts/sync-agent-rules.sh

# Drift guard: fail if AGENTS.md or Cursor symlinks are stale
agents-check:
    ./scripts/sync-agent-rules.sh --check
```

## Why not just symlink `.claude/rules` to `.ai/rules`?

Tried it. Claude Code at project level only auto-loads `AGENTS.md` (or `CLAUDE.md`) — not a `.claude/rules/` directory. Codex and Gemini behave the same. Only Cursor honours a project rules directory. So the answer is: symlink for Cursor, render into AGENTS.md for the rest.
