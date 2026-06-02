# Bug-Hunt Criteria

The defect-finding lens: what could break when this change lands. Threads T1–T4 in the workflow each own one section below. The model is good at surface issues and bad at these — note the non-obvious ones.

_Merged from `premerge-review` (review-criteria.md + SKILL.md checklists), originally promoted from `.ai/rules/process/code-review.mdc`._

## Fix-First Classification

Classify every finding before reporting:

| Classification | Action | Criteria |
|---------------|--------|----------|
| **AUTO-FIX** | Fix silently | A senior engineer would apply without discussion. Mechanical, unambiguous. |
| **ASK** | Report and recommend | Reasonable engineers could disagree. Trade-offs, architecture, judgment. |

### AUTO-FIX Examples (just fix)

- Unused imports/variables, dead code, import ordering
- Formatting/naming inconsistencies with surrounding code
- Missing error context in log statements
- Obvious null guards at system boundaries
- Deprecated API with a drop-in replacement

### ASK Examples (report, don't touch)

- Architectural changes (new abstractions, data flow)
- Security-sensitive changes (auth, validation, secrets)
- API surface changes (new endpoints, changed contracts)
- Dependency additions or removals
- Test strategy decisions

**Default to ASK when uncertain.** Batch ASK findings into a single summary; never make a judgment-call change silently.

## T1 — Correctness (the non-obvious)

- **Race conditions** — shared mutable state, check-then-act, TOCTOU
- **Off-by-one** — fenceposts, inclusive vs. exclusive ranges, pagination boundaries
- **Floating-point for money** — use integers/decimals
- **Ordering assumptions** — async operations, event handlers, map iteration order
- **Type assertions lying about reality** — `as any`, unsafe casts, non-null `!` on nullable values
- **Error paths** — is the failure case handled, or only the happy path? Are errors swallowed?

## T2 — Security (what models routinely miss)

- **IDOR** — can a user reach another user's resource by changing an ID?
- **Timing-safe comparison** for secrets/tokens (constant-time equality)
- **ReDoS** — catastrophic backtracking on user-supplied regex input
- **Deserialization safety** on untrusted data
- **Response body filtering** — allowlists not blocklists for serialized fields (no leaking internal fields)
- **CORS** not `*` in production
- **Injection** — parameterized queries, escaped shell/HTML, no string-built SQL

## T3 — Data Integrity

- Is the migration backwards-compatible? (can old code run against the new schema during deploy?)
- Is data loss possible? (column drops, type narrowing, cascade deletes)
- Is there a rollback path for this migration?
- Are default values sensible for existing rows?

## T4 — Operational Readiness

- Works in production, not just locally? (env vars, paths, permissions, TLS)
- Structured logs at key decision points with correlation IDs?
- Timeouts and retries configured? (no unbounded waits; backoff on retries)
- What happens when a dependency fails? (graceful degradation vs. crash)
- Blast radius? (one user, one tenant, all users?)
- Deployment concern? (feature flag, config change, ordering dependency?)
- Rollback plan? (revert, flag off, migration rollback, or "hope"?)
- Safe to deploy on a Friday? If not, why?

## Severity

- **Critical** — must fix before merge
- **Warning** — should fix
- **Note** — consider
