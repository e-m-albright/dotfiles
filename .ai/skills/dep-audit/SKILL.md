---
name: dep-audit
description: Audit project dependencies for outdated versions, vulnerabilities, and license issues across all stacks
disable-model-invocation: true
---

# Dependency Audit

Audit a project's dependencies for security vulnerabilities, outdated versions, and license concerns. Auto-detects the stack and runs the appropriate tools.

## Workflow

1. Detect project stack from lock/manifest files:

| File | Stack | Audit command |
|------|-------|---------------|
| `package-lock.json` / `yarn.lock` / `pnpm-lock.yaml` | Node | `npm audit`, `npx depcheck` |
| `bun.lockb` | Bun | `bun audit` (if available), else `npx depcheck` |
| `go.sum` | Go | `govulncheck ./...`, `go list -m -u all` |
| `Cargo.lock` | Rust | `cargo audit`, `cargo outdated` |
| `uv.lock` / `requirements.txt` | Python | `pip-audit`, `uv pip list --outdated` |

2. Run available audit tools (skip gracefully if a tool isn't installed)

3. Compile a unified report:

```
## Vulnerabilities (action required)
- [HIGH] package@version — CVE-XXXX: description
  Fix: upgrade to package@fixed-version

## Outdated (review)
- package: current → latest (major/minor/patch)

## Unused (candidates for removal)
- package — not imported anywhere

## License concerns
- package@version — GPL-3.0 (copyleft in an MIT project)
```

4. Suggest a remediation plan ordered by severity

## Notes

- Install missing tools: `brew install govulncheck`, `cargo install cargo-audit cargo-outdated`, `uv tool install pip-audit`
- For monorepos, check each workspace/module independently
- Never auto-fix — report only, let the user decide
