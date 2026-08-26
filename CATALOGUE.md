# Feature Catalogue

Canonical map of maintained host capabilities in this repository. Update the affected row when a capability is added, removed, materially expanded, split, or consolidated.

## Counting method

Counts are physical lines in the current working tree, including comments and blank lines. Implementation includes Python, shell, and launcher code. Tests are counted separately. Config/data includes the package manifest and user-facing shell, Git, terminal, and editor configuration. Documentation is not included in line totals. Attribution is file-based; shared CLI files remain in a shared row. In-progress files present in the working tree are included when they already participate in the verified command path.

## Registry

| Capability | Implementation | Tests | Config/data | Total | Posture |
|---|---:|---:|---:|---:|---|
| Package manifest, installation, drift, upgrade, and prune | 1,124 | 1,692 | 322 | 3,138 | Core; strongest and most heavily tested subsystem |
| Host doctor and configuration repair | 507 | 478 | 0 | 985 | Core |
| Tailscale, Paseo, private-site, and sleep-control operations | 536 | 497 | 0 | 1,033 | Core for remote continuity |
| TypeWhisper installation and configuration | 504 | 195 | 74 | 773 | Active; keep isolated from generic package logic |
| Fresh-Mac bootstrap and macOS configuration | 808 | 89 | 0 | 897 | Core; shell-heavy boundary merits smoke coverage |
| CLI application, banner, adapters, rendering, and test fakes | 465 | 498 | 0 | 963 | Supporting platform |
| Command launchers and Just recipes | 509 | 0 | 0 | 509 | Core entry points |
| Shell, Git, terminal, editor, and completion configuration | 0 | 0 | 813 | 813 | Core desired state |
| Password generation and clipboard utility | 69 | 80 | 0 | 149 | Small and complete |

## Capability map

### Package lifecycle

- Declarative Homebrew formula, cask, tap, Go, npm, and special-installer inventory.
- Feature flags, disabled dated tombstones, installed and missing inventory, stale-item reporting, upgrades, cleanup, and confirmed pruning.
- Verified TypeWhisper download and signing identity checks.
- Workbench installation as a pinned adjacent public capability.

**Assessment:** Keep. This is the repository's deepest module and earns its size through fail-closed inventory handling and dry-run/confirmation behavior. Continue pruning disabled software through tombstones rather than deleting historical intent.

### Host bootstrap and desired state

- Fresh-Mac installer and idempotent symlink helpers.
- macOS preferences, Dock, login items, file associations, SSH, OrbStack, and Yazi setup.
- Shell prompt and aliases, Git defaults and global ignore rules, Ghostty, Zed, and completions.
- Generic discovery of an optional private automation layer without publishing its repository name.

**Assessment:** Keep. The installer remains necessarily procedural, but private workflow details must stay behind environment variables or generic discovery. Add focused shell tests when bootstrap behavior changes; do not migrate stable native configuration into Python merely for uniformity.

### Doctor

- Runtime, editor, shell, Node, Python, Workbench, remote-access, and launcher checks.
- Bounded repair for symlinks and configuration drift.
- Human-readable grouped output and actionable repair hints.

**Assessment:** Keep. Doctor is the main reconciliation surface and should remain an observer plus narrow repair tool, not a second installer.

### Remote continuity

- Tailscale status and connection management.
- Paseo launch-agent installation, status, password rotation, and stale-binding repair.
- Tailnet-only private site support and caffeine status.

**Assessment:** Keep. It owns a distinct operational boundary. Preserve dry runs, explicit failures, and tailnet checks. Do not reintroduce a general terminal multiplexer without a measured need.

### TypeWhisper

- Verified installation, signing validation, tracked settings, workflow application, and fallback behavior.

**Assessment:** Keep while used. It is correctly isolated because its distribution and configuration semantics differ from Homebrew. Review if the vendor gains a stable package and native configuration interface.

### CLI platform and utilities

- Typer command tree, application context, process port and adapter, result rendering, fakes, and compatibility shell launchers.
- Password generation with optional clipboard copy.

**Assessment:** Keep. The platform is small relative to its test coverage. Avoid creating additional generic service layers unless another command needs the same effect boundary.

## Review triggers

- Retire a package through a dated disabled manifest entry, then prune it explicitly.
- Review TypeWhisper's special installer when a trustworthy native package appears.
- Review remote-control code if Paseo or Tailscale no longer owns the active path.
- Treat private paths or repository names in tracked public files as privacy defects.
- Keep shell bootstrap and Python reconciliation as separate layers unless duplicated behavior causes actual drift.
