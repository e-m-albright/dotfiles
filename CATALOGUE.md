# Feature Catalogue

Timestamped map of maintained host capabilities in this repository.

**Snapshot:** 2026-09-19. Refresh the map and counts on demand during an explicit capability-health review, not during routine implementation.

## Scale snapshot

Counts are physical lines in the reviewed working tree, including the new files in this change, comments, and blank lines. Symlinks count as their one-line Git representation rather than duplicating their target. Empty files are text with zero lines. Every file belongs to exactly one group; ignored local artifacts and caches are excluded:

- **Code - source:** executable implementation and styling maintained here.
- **Code - tests:** executable verification, including test helpers and fixtures.
- **Text:** documentation, instructions, configuration, manifests, and other human-maintained text.
- **Generated/vendor:** generated dependency state or third-party code retained in the repository.

Binary assets are reported by file count and bytes, not fake line counts. Attribution is file-based; these repository totals deliberately avoid speculative per-capability splitting.

| Group | Files | Lines |
|---|---:|---:|
| Code - source | 40 | 4,538 |
| Code - tests | 35 | 5,070 |
| Text | 35 | 2,559 |
| Generated/vendor | 1 | 804 |
| **Text total** | **111** | **12,971** |

Binary assets: 0 files. SVG and empty files are counted as text.

## Registry

| Capability | Posture |
|---|---|
| Package manifest, installation, drift, upgrade, and prune | Core; strongest and most heavily tested subsystem |
| Host doctor and configuration repair | Core |
| Local credential inventory and secure enrollment | Active; bounded host security capability |
| Tailscale, Paseo, private-site operations, and Caffeine status | Core for remote continuity |
| Fresh-Mac bootstrap and macOS configuration | Core; isolated tests cover orchestration and recovery |
| Local inference host provisioning | Active; supervised use with bounded service reconciliation |
| CLI application, banner, adapters, rendering, and test fakes | Supporting platform |
| Command launchers and Just recipes | Core entry points |
| Shell, Git, terminal, editor, and completion configuration | Core desired state |
| Password generation and clipboard utility | Small and complete |

## Capability map

### Package lifecycle

- Declarative Homebrew formula, cask, tap, Go, npm, and special-installer inventory, including the active open-source MLX inference runner.
- Feature flags, disabled dated tombstones, installed and missing inventory, stale-item reporting, upgrades, cleanup, and confirmed pruning.
- TypeWhisper supplies local dictation; OpenWhispr remains a disabled dated tombstone.
- Workbench installation pinned for fresh clones; existing working checkouts are preserved.

**Assessment:** Keep. This is the repository's deepest module and earns its size through strict manifest validation, fail-closed inventory handling, and dry-run/confirmation behavior. Continue pruning disabled software through tombstones rather than deleting historical intent. Explicitly desired tools remain declared; absence of tracked usage alone is insufficient evidence for retirement.

### Host bootstrap and desired state

- Fresh-Mac installer and idempotent symlink helpers.
- macOS preferences, Dock, login items, file associations, SSH, OrbStack, and Yazi setup.
- Shell prompt and aliases, Git defaults and global ignore rules, Ghostty, Zed, and completions.
- Generic discovery of an optional private automation layer, shared as a contract by bootstrap and Doctor, with an explicit root override.

**Assessment:** Keep. The installer remains necessarily procedural, but private workflow details must stay behind environment variables or generic discovery. Add focused shell tests when bootstrap behavior changes; do not migrate stable native configuration into Python merely for uniformity.

### Doctor

- Runtime, editor, shell, Node, Python, Workbench, remote-access, and launcher checks.
- Bounded repair for symlinks and configuration drift.
- Bounded diagnostic subprocesses, warnings for failed version probes, and actionable repair hints.

**Assessment:** Keep. Doctor is the main reconciliation surface and should remain an observer plus narrow repair tool, not a second installer.

### Remote continuity

- Tailscale status and connection management.
- Paseo launch-agent installation, status, password rotation, stale-binding repair, and verified shutdown.
- Tailnet-only private site support and caffeine status.

**Assessment:** Keep. It owns a distinct operational boundary. Preserve dry runs, explicit failures, and tailnet checks. Do not reintroduce a general terminal multiplexer without a measured need.

### Credential lifecycle

- Machine-local, metadata-only inventory of revocable grants, consumers, scopes, expiry, rotation, and restoration instructions.
- Secure enrollment into macOS Keychain, command-based Pi references, and single-child-process injection without secret arguments or durable environment files.
- Credential status in Doctor without reading or printing secret values.
- Private atomic file publication and an allowlisted environment for persisted Pi auth checks.

**Assessment:** Keep. This closes a recurring host-level secret-management gap while leaving OAuth token ownership and CI secrets with their native platforms. Preserve the documented limitation that Keychain does not isolate mutually untrusted processes running as the same macOS user.

### Local inference host provisioning

- oMLX grammar installation and a bounded vendor-loader repair.
- Non-secret settings overlay, selected model weights, and service readiness checks.
- Restart intent preserved across failures so reruns recover incomplete setup.

**Assessment:** Keep. Host provisioning belongs here; agent model routing remains with Workbench. Supervised use is accepted, while physical network-disconnect acceptance and autonomous operational accuracy remain open. Retire the loader workaround only after confirming upstream parity.

### CLI platform and utilities

- Typer command tree, application context, process port and adapter, result rendering, fakes, and compatibility shell launchers.
- Password generation with optional clipboard copy.
- Real CLI tests with an empty home and PATH run in the ordinary local and CI suite.

**Assessment:** Keep. The platform is small relative to its test coverage. Avoid creating additional generic service layers unless another command needs the same effect boundary.

## Review triggers

- Retire a package through a dated disabled manifest entry, then prune it explicitly.
- Review remote-control code if Paseo or Tailscale no longer owns the active path.
- Treat private paths or repository names in tracked public files as privacy defects.
- Keep shell bootstrap and Python reconciliation as separate layers unless duplicated behavior causes actual drift.
