# Security Audit Synthesis

You are synthesizing findings from a deterministic security audit run. Tools have already executed; their JSON output is in `raw.json` and per-tool files alongside it.

## Inputs

- `raw.json` — metadata + per-tool status (ok / findings / error / not-installed)
- `osv-scanner.json`, `gitleaks.json`, `semgrep.json`, `trivy.json` — per-tool detail
- (Plus any language-specific scanners the project added: `cargo-deny-*.json`, `pip-audit.json`, `bandit.json`)

## What to produce

Write `findings.md` next to `raw.json`. Structure:

```markdown
# Security Audit — <ts>

**Tools run**: [list with status]
**Tools missing**: [list with install_cmd]
**Total findings**: [count by severity]

## Critical / High

### [Finding title]
- **Tool**: osv-scanner / semgrep / ...
- **Where**: file:line, package@version, etc.
- **What**: 1-2 sentence description
- **Why it matters**: actual exploit path or compliance impact
- **Fix**: specific remediation (upgrade to X, patch Y, suppress with justification)

## Medium / Low

[Same structure, condensed]

## Tool gaps

[Tools that didn't run because they're not installed — note which threat surfaces are uncovered as a result]

## Recommendations

1. [Top 3 actions, prioritized by exploitability × blast radius]
```

## Rules

- Do NOT modify code. Findings only.
- Cite the originating tool by name and the JSON file when relevant.
- Distinguish CVE severity from contextual exploitability ("CVE is High but the affected code path isn't reachable from production input").
- If `gitleaks` reports secrets, flag them as **Critical** regardless of the tool's severity.
- If `trivy` finds container/IaC misconfigs, group them separately from dependency CVEs.
- Reference principles from `docs/engineering-philosophy.md` where applicable (especially #4 Boundaries are contracts, #7 Every exception is an event).

## Branch convention

After writing `findings.md`, commit on a branch named `audit/security-<ts>`. Fixes branch separately as `audit-fix/security-<ts>` off `main` — never modify the findings branch.
