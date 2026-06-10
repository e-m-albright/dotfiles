---
name: audit-agent-fleet-drift
description: Agent-fleet drift audit — the capability matrix vs reality: probes that no longer agree with their claim, vendor features shipped since last review, and uniformity gaps that regressed
---

# Agent Fleet Audit: Drift From Reality

You are auditing the cross-vendor agent capability picture for drift. The matrix in
`cli/src/dotfiles/cmd/agent/capability_matrix.py` claims what each vendor (Claude,
Cursor, Codex, Antigravity/agy, Pi) supports, and every cell carries a **receipt**
(a local probe and/or a source URL). This serves **"tethered to reality"**: a claim
is only as good as the probe that still proves it. Vendors ship fast — the matrix
rots silently unless it is re-proven on a cadence.

## What to look for

### Probes that no longer agree with their claim
- Run `dotfiles agent capabilities --verify`. Every `DRIFT` line is a finding: a
  cell claims `yes`/`beta`/`ext` but its probe now fails (or claims `no` but the
  probe now passes). The tool already classifies agree vs drift — report each drift
  with the capability, vendor, the probe command, and what it returned.

### Stale matrix — vendor features shipped since last review
- Read the `Last reviewed` date in `docs/knowledge/agent-fleet.md`. If
  `dotfiles agent overview` shows the staleness warning (>90d), the landscape needs
  a re-check.
- For each vendor, check release notes / changelogs (Claude Code, Cursor, Codex,
  Antigravity, Pi) since that date for new capabilities in the enforced tier
  (rules, skills, subagents, statusline, permissions, hooks) or the wider matrix
  (mcp, plugins, dynamic-workflows, memory, output-styles, slash-commands,
  sandboxing, model-routing). A capability we mark `no`/`unverified` that has since
  shipped is a finding — with the source URL.

### Uniformity gaps that regressed
- Run `dotfiles agent overview` and read the **Uniformity (enforced)** matrix.
  A cell that was `✓` (deployed) and is now `✗` (closable gap) is a regression —
  a deploy step broke or a path moved. Report the capability + vendor + the probe
  in `overview.py:_deployment_state` that flipped.
- A `○` (workspace-local/ext/beta) cell that has become globally deployable because
  the vendor shipped a global mechanism is the inverse finding: now closable.

### Source-only cells that became locally probeable
- Cells with a `src` URL but no `test` are unverified on-machine. If the capability
  is now installed locally and could be probed (binary `strings`, `--help` grep,
  config check), propose the probe so the cell graduates from cited to tested.

## How to report

For each finding: the capability + vendor, the matrix cell's current claim, the
**evidence** that contradicts it (the failing/passing probe output, or a changelog
URL with date), **severity** (wrong-claim-shipping / stale-but-harmless / cosmetic),
and the fix — update the cell + its probe/source, or wire a new deploy step for a
now-closable gap. Re-run `dotfiles agent capabilities --verify` after any matrix
edit and confirm it reports `0 DRIFT`. Refresh the `Last reviewed` date in
`docs/knowledge/agent-fleet.md` when the sweep is complete.

Findings open an issue or a draft PR for human review. Never auto-merge, and never
loosen a probe just to make `--verify` pass — fix the claim to match reality.
