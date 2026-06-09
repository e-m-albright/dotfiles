---
name: audit-observability
description: Observability-coverage audit — are significant operations traced/logged with structured context? silent failure paths, bare string logs, missing spans on critical paths, swallow-and-continue
---

# Operations Audit: Observability Coverage

You are auditing this codebase for observability gaps — places where a significant operation can fail or complete invisibly. Serves **P9 (Observability is a design constraint)** and **P7 (Every exception is an event)**.

## What to look for

### Silent Failure Paths
- `except Exception` / `.catch(() => {})` / `if err != nil { return }` that swallows and continues with no log or event
- Fallback/default-on-error branches that hide that anything went wrong
- Empty catch blocks with no comment justifying intentional, bounded recovery

### Bare String Logs
- `log.info("done")` / `print(...)` with no structured context — no entity IDs, operation name, or outcome
- Bare string warnings/errors where the message can't be searched or correlated
- Inconsistent log levels (errors logged at info, routine events at warn)

### Missing Spans on Critical Paths
- Request handlers, queue/worker jobs, external API calls, and DB transactions with no span/trace
- Long or fan-out operations where you can't tell which step is slow or failing
- Critical user flows where a failure produces no telemetry to debug from

### Swallow-and-Continue Without an Event
- Retries, circuit-breakers, or degraded-mode paths taken with no metric/log marking them
- Skipped/dropped records in a pipeline with no count or sample logged
- Timeouts and cancellations handled but never recorded

## How to report

For each finding: `file:line`, the gap class, **severity** (will-fail-invisibly / hard-to-debug / nit), what context is missing (which IDs, span name, level), and the fix — add the span, replace the bare log with structured fields, or turn the silent catch into a logged, bounded event. NEVER auto-apply the change.

Findings open an issue or a draft PR for human review. Never auto-merge, and never auto-apply a generative refactor.
