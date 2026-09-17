# Feature Catalogue

Timestamped map of maintained host capabilities in this repository.

**Snapshot:** 2026-09-07. Refresh the map and counts on demand during an explicit capability-health review, not during routine implementation.

## Scale snapshot

Counts are physical lines in tracked text blobs, including comments and blank lines. Tracked symlinks count as their one-line Git blob rather than duplicating their target. Every tracked file belongs to exactly one group:

- **Code - source:** executable implementation and styling maintained here.
- **Code - tests:** executable verification, including test helpers and fixtures.
- **Text:** documentation, instructions, configuration, manifests, and other human-maintained text.
- **Generated/vendor:** generated dependency state or third-party code retained in the repository.

Binary assets are reported by file count and bytes, not fake line counts. Attribution is file-based; these repository totals deliberately avoid speculative per-capability splitting.

| Group | Files | Lines |
|---|---:|---:|
| Code - source | 35 | 4,348 |
| Code - tests | 26 | 3,857 |
| Text | 33 | 2,589 |
| Generated/vendor | 1 | 808 |
| **Tracked text total** | **95** | **11,602** |

Binary assets: 9 tracked files, 4,119 bytes.

## Registry

| Capability | Posture |
|---|---|
| Package manifest, installation, drift, upgrade, and prune | Core; strongest and most heavily tested subsystem |
| Host doctor and configuration repair | Core |
| Local credential inventory and secure enrollment | Active; bounded host security capability |
| Tailscale, Paseo, private-site, and sleep-control operations | Core for remote continuity |
| Fresh-Mac bootstrap and macOS configuration | Core; shell-heavy boundary has focused plan coverage |
| CLI application, banner, adapters, rendering, and test fakes | Supporting platform |
| Command launchers and Just recipes | Core entry points |
| Shell, Git, terminal, editor, and completion configuration | Core desired state |
| Password generation and clipboard utility | Small and complete |

## Capability map

### Package lifecycle

- Declarative Homebrew formula, cask, tap, Go, npm, and special-installer inventory, including the active open-source MLX inference runner.
- Feature flags, disabled dated tombstones, installed and missing inventory, stale-item reporting, upgrades, cleanup, and confirmed pruning.
- OpenWhispr CLI installation through the ordinary pinned npm inventory; the desktop application remains outside bespoke host automation.
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
- Review remote-control code if Paseo or Tailscale no longer owns the active path.
- Treat private paths or repository names in tracked public files as privacy defects.
- Keep shell bootstrap and Python reconciliation as separate layers unless duplicated behavior causes actual drift.
