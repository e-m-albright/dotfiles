---
name: audit-docs-drift
description: Docs-drift audit — README/AGENTS/docs that no longer match the code: dead commands/flags, stale paths, examples that won't run, out-of-date public API surface
---

# Documentation Audit: Drift From Code

You are auditing this codebase for documentation that no longer matches the code. Serves **P3 (One source of truth per concept)**, generalized from code to docs: the docs describe the system, so they must derive from — and agree with — the real thing.

## What to look for

### Documented Commands & Flags That Don't Exist
- Commands, subcommands, scripts, or task-runner recipes in the README that aren't defined anywhere
- CLI flags/options documented but absent from the parser, or renamed/removed in code
- Env vars described in docs that the code never reads (and vice versa)

### Stale File Paths & Structure
- References to files, directories, or modules that have moved or been deleted
- "Project layout" / architecture sections describing a tree that no longer exists
- Broken intra-repo links in README / AGENTS / docs

### Examples That Won't Run
- Code snippets calling functions/APIs whose signatures changed
- Quickstart / install steps referencing removed scripts, wrong paths, or old versions
- Config examples with keys the loader no longer recognizes

### Out-of-Date Public API Surface
- Documented public functions/endpoints/types that were removed, renamed, or had params change
- New public surface that exists in code but is undocumented (drift in the other direction)
- Version numbers, supported-platform lists, or dependency requirements that lag the actual manifests

## How to report

For each finding: the doc location (`file:line`) AND the code location it contradicts (`file:line`), **severity** (will-mislead-a-new-user / stale-but-harmless / cosmetic), and the fix — update the doc to match code, or flag that the code change dropped a documented contract. NEVER auto-apply the edit. Prefer fixing the doc to match code unless the code change itself was the regression, in which case flag it for a human.

Findings open an issue or a draft PR for human review. Never auto-merge, and never auto-apply a generative refactor.
