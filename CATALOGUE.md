# Feature Catalogue

Timestamped map of maintained host capabilities in this repository.

**Snapshot:** 2026-09-03. Refresh the map and counts on demand during an explicit capability-health review, not during routine implementation.

## Counting method

Counts are physical lines at snapshot time, including comments and blank lines. Implementation includes Python, shell, and launcher code. Tests are counted separately. Config/data includes the package manifest and user-facing shell, Git, terminal, and editor configuration. Documentation is not included in line totals. Attribution is file-based; shared CLI files remain in a shared row. In-progress files present in the working tree are included when they already participate in the verified command path.

## Registry

| Capability | Implementation | Tests | Config/data | Total | Posture |
|---|---:|---:|---:|---:|---|
| Package manifest, installation, drift, upgrade, and prune | 1,191 | 1,718 | 378 | 3,287 | Core; strongest and most heavily tested subsystem |
| Host doctor and configuration repair | 549 | 512 | 0 | 1,061 | Core |
| Local credential inventory and secure enrollment | 552 | 605 | 0 | 1,157 | Active; bounded host security capability |
| Tailscale, Paseo, private-site, and sleep-control operations | 538 | 497 | 0 | 1,035 | Core for remote continuity |
| TypeWhisper installation and configuration | 599 | 268 | 102 | 969 | Active; keep isolated from generic package logic |
| Fresh-Mac bootstrap and macOS configuration | 881 | 149 | 0 | 1,030 | Core; shell-heavy boundary has focused plan coverage |
| CLI application, banner, adapters, rendering, and test fakes | 489 | 495 | 0 | 984 | Supporting platform |
| Command launchers and Just recipes | 341 | 0 | 0 | 341 | Core entry points |
| Shell, Git, terminal, editor, and completion configuration | 0 | 0 | 838 | 838 | Core desired state |
| Password generation and clipboard utility | 69 | 80 | 0 | 149 | Small and complete |

## Capability map

### Package lifecycle

- Declarative Homebrew formula, cask, tap, Go, npm, and special-installer inventory, including the active open-source MLX inference runner.
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
- Loopback API and CLI recovery runbook with token-authentication and privacy boundaries.

**Assessment:** Keep while used. It is correctly isolated because its distribution and configuration semantics differ from Homebrew. Review if the vendor gains a stable package and native configuration interface.

### Credential lifecycle

- Machine-local, metadata-only inventory of revocable grants, consumers, scopes, expiry, rotation, and restoration instructions.
- Secure enrollment into macOS Keychain, command-based Pi references, and single-child-process injection without secret arguments or durable environment files.
- Credential status in Doctor without reading or printing secret values.

**Assessment:** Keep. This closes a recurring host-level secret-management gap while leaving OAuth token ownership and CI secrets with their native platforms. Preserve the documented limitation that Keychain does not isolate mutually untrusted processes running as the same macOS user.

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
