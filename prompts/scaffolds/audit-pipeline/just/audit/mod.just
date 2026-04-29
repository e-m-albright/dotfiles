set working-directory := "../../"

# Audit pipeline: tool-first findings + LLM synthesis.
#
# Each recipe runs deterministic tools and writes raw.json under
# .ai/artifacts/audits/<topic>/<ts>/. The LLM synthesis pass (audit prompt at
# .ai/prompts/audits/<topic>.md) reads raw.json and produces findings.md.
#
# Branch convention:
#   audit/<topic>-<ts>      — immutable findings snapshot
#   audit-fix/<topic>-<ts>  — fixes branched off main, never off audit/*

[private]
@default:
    just --list audit

# Run all baseline audits.
all:
    just audit security
    just audit ai-usage

# security: deterministic security tools (osv-scanner, gitleaks, semgrep, trivy).
security:
    bash scripts/audit/security.sh

# ai-usage: token budget, frontmatter, dead links across .ai/ and AGENTS.md.
ai-usage:
    python3 scripts/audit/ai_usage.py

# baselines: ratchet check — every metric in baselines.json must hold or improve.
baselines:
    python3 scripts/check_baselines.py

# auto-ratchet: monotonically tighten baselines.json to current state.
# Run after merging a cleanup PR. Never raises a ceiling, only lowers.
auto-ratchet:
    python3 scripts/check_baselines.py --auto-ratchet

# converge: tighten baselines + run all audits in sequence.
# Recommended cadence: weekly via scheduled trigger.
converge:
    @echo "── auto-ratchet (lock in any improvements) ──"
    -just audit auto-ratchet
    @echo ""
    @echo "── audits ──"
    -just audit all
    @echo ""
    @echo "Convergence pass complete. Review .ai/artifacts/audits/ for findings."
