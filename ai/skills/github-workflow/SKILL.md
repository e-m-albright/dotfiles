---
name: github-workflow
description: GitHub and PR workflow conventions using the gh CLI — PR creation, code review, CI monitoring, and compliance-aware secrets handling. Use when opening or reviewing a PR, running `gh pr create` / `gh pr checkout` / `gh run watch`, linking Linear or GitHub issues, monitoring CI from the terminal, touching GitHub Actions workflows or secrets, or when the user says "open a PR", "review this PR locally", "check CI status", "how do I handle secrets in Actions".
---

# GitHub & Workflow

## Pull Requests

- Use `gh pr create` for PRs. Keep titles concise and descriptions audit-friendly (intent, risk, verification).
- Don't skip required CI checks or approval gates — Drata compliance may depend on them.
- Avoid force-pushing to `main`/`master` without explicit instruction; it rewrites shared history others may have built on.

## Issues & Incidents

- Reference Linear or GitHub Issues by ID when closing or linking work.
- Be aware of Rootly incident tracking — confirm before auto-closing issues that may be tied to an active incident.

## Code Review

- Use `gh pr checkout <number>` to review PRs locally.
- When suggesting changes in review, prefer concrete diffs over vague descriptions.

## CI & Actions

- Use `gh run list` / `gh run watch` to monitor workflow status from the terminal.
- Understand the full trigger matrix before modifying GitHub Actions workflows — a change can fire (or silently stop firing) jobs you didn't intend.

## Secrets & Config

- Use Doppler or GitHub Actions secrets for sensitive values — hardcoding them in workflow files leaks them into history and logs.
- For org-level secrets, check existing patterns before proposing new secret names.

_Promoted from `.ai/rules/process/github-workflow.mdc` (was an always-on rule; now an on-demand skill)._
