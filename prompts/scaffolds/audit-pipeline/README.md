# Audit Pipeline Scaffold

Two-phase audit pattern lifted from Ophira and made portable. **Phase 1** runs deterministic tools and writes structured JSON to `.ai/artifacts/audits/<topic>/<ts>/raw.json`. **Phase 2** is an LLM synthesis pass that reads `raw.json` and writes a human-readable `findings.md`.

## What this scaffold deploys

```
scripts/audit/
├── security.sh       # osv-scanner + gitleaks + semgrep + trivy → raw.json
└── ai_usage.py       # token budget + frontmatter + dead-link checks → raw.json

just/audit/
└── mod.just          # `just audit security`, `just audit ai-usage`, `just audit converge`

.ai/prompts/audits/
├── security.md       # synthesis prompt for security findings
└── ai-usage.md       # synthesis prompt for ai-usage findings
```

## Usage

```bash
just audit security        # run security tools, write raw.json
# Then: open .ai/prompts/audits/security.md and have your agent synthesize findings.md
```

## Branch convention

- `audit/<topic>-<ts>` — immutable findings snapshot. Don't modify after creation.
- `audit-fix/<topic>-<ts>` — fixes branched off `main`, never off `audit/*`.

## Customization

Each `scripts/audit/*.{sh,py}` is project-owned after scaffolding. Add language-specific scanners (cargo-deny for Rust, pip-audit + bandit for Python, npm audit for Node) by extending the `run_tool` calls in `security.sh`.

## Recurring runs

For Claude Code users: schedule weekly via `claude.ai/code/scheduled` triggers running `just audit converge`. The convergence pass auto-ratchets baselines (if installed) and reports stagnation.
