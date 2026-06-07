# The Canon & the Catechism

> One name for all our best designs and ambitions — process, code health, developer
> experience, and the toolbelt that enforces them. Say **"the Canon"** and mean: *this.*
> Everything in this repo that is a considered choice about how we build — the agent
> kernel, the skills and subagents, the rules, the code-health lenses, the justfiles,
> the hooks, the CI — is either an **article** of the Canon or a **rite** of the Catechism.

## The two words

- **The Canon** — *what we believe is true.* Doctrine. It answers **why**, changes rarely,
  and only by argument. The articles below.
- **The Catechism** — *what we do about it.* Practice. It answers **what do I do now**,
  in call-and-response form. The rites below.

**The binding law:** every rite traces to an article, and every article has at least one
rite that enacts it. A practice with no article behind it is superstition; an article with
no rite is a claim we can't keep — which is exactly what the Canon means by *"if you cannot
enforce it, do not claim it."* The two halves are the same doctrine, once as belief and
once as muscle memory. **Believe the Canon; practice the Catechism.**

---

## The Canon — the articles

### I. On how we work — the agent kernel
*Full text: [`ai/agents/shared/rules.md`](ai/agents/shared/rules.md), deployed verbatim to every vendor.*

1. **Verify before claiming done.** Evidence before assertions; run it and show the output.
2. **Brainstorm before building; plan multi-step work.** Confirm intent and approach first.
3. **Minimize surface area.** The smallest change that solves the request.
4. **Build on bedrock, not quicksand.** Fix root causes; suppressions are never the first move.
5. **No competing versions.** A replacement deletes its predecessor in the same change.
6. **Don't game metrics.** Satisfy the check's intent, never weaken it to pass.
7. **Respect existing conventions; debug systematically.** Reproduce, hypothesize, test.
8. **No sycophancy; calibrate confidence.** Say what you know, flag what you don't.

### II. On what good code is — the twelve principles
*Full text + a gate for each: [`docs/engineering-philosophy.md`](docs/engineering-philosophy.md).*

1. The compiler is the first reviewer.
2. Type the domain, not the plumbing.
3. One source of truth per concept.
4. Boundaries are contracts.
5. Simplicity is the goal — small files are a proxy.
6. Dead code is dead weight.
7. Every exception is an event.
8. Concurrency is bounded.
9. Observability is a design constraint, not an afterthought.
10. Suppressions ratchet downward.
11. Tests verify behavior, not implementation.
12. Convention over configuration over code.

### III. On how we enforce — the toolbelt doctrine
*Full text: [`docs/knowledge/engineering-gates.md`](docs/knowledge/engineering-gates.md).*

1. **Gate the delta, not the backlog.** Grandfather existing debt; block regressions; ratchet the ceiling down.
2. **The ratchet only falls.** Every metric ceiling is monotonic; raising one needs an auditable, justified bump.
3. **CI calls task-runner recipes; YAML holds zero logic.** One definition, three consumers — CI, hooks, humans.
4. **One source of truth, generated outward.** Contracts, registries, baselines: authored once, derived everywhere.
5. **Cost-aware verification.** Tier tests by execution cost; run only what a change affects.

---

## The Catechism — the rites

*Where the doctrine becomes practice. Each rite enacts one or more articles above.*

### The lenses — code health
The contestable lenses for improving a codebase, routed by the [`code-health`](ai/skills/code-health/SKILL.md)
skill: the form lenses (`form-deepen`, `form-tidy`, `form-prune`, `form-clarify`, `form-align`,
`form-purify`), the measured engine (`converge`), and the function/safety/speed tier
(`review`, `/security-review`, `diagnose`, `performance-engineer`). The full theory —
two-axis model, antagonist tiebreaks, the convergent sequence — is the
[portfolio](docs/knowledge/code-health-portfolio.md).
**Call-and-response:** `dotfiles agent catechism` (or the
[entry-point map](docs/knowledge/code-health-portfolio.md#entry-points--the-catechism)).

### The toolbelt — the liturgy of enforcement
- **`justfile`** — the recipes. Every gate (`fmt`, `lint`, `types`, `deadcode`, `complexity`,
  `ratchet`, `test`) is one `just` recipe, so CI, hooks, and humans run identical commands.
- **`lefthook.yml`** — the hooks. `just check --fast` at pre-commit, `just check` at pre-push.
- **`.github/workflows/ci.yml`** — CI. The `cli` job runs `just check`, so the ratchet,
  complexity ceiling, and coverage floor are CI-enforced invariants, not local social contracts.
- **`docs/health/<scope>/`** — persistent state: `baselines.json` (the ratchet), `findings.md`
  (the ledger), `report-<date>.md` (the graded snapshot).

### The routines — self-managing convergence
- **Adopt:** `dotfiles agent health` bootstraps any repo's health backbone in one command.
- **Enforce:** the ratchet gate (`just ratchet`, wired into `just check`).
- **Detect, don't auto-fix:** schedule the *finding* (scorecard + audits → issue/draft PR);
  gate the *fixing*. Generative refactoring is never auto-applied.

### The wider rite-set — agents, skills, rules, DX
The skills (`ai/skills/`), subagents (`ai/subagents/`), shared rules, MCP servers, permission
profiles, and project-file conventions (`ai/skills/project-files`) are all rites — each a
considered practice that enacts an article. New ones earn their place by tracing to one.

---

## Say the word

When the owner says **"the Canon,"** **"is this in the Canon?"**, or **"add this to the
Catechism,"** it means *this whole system* — the documented philosophy and practice for how
we build here. Adding a rite means: name the article it serves, or it doesn't belong. Adding
an article means: name the rite that will enforce it, or don't claim it.

- The independent verdict on the code-health half: [`docs/health/ASSESSMENT.md`](docs/health/ASSESSMENT.md).
- The persistent-state convention: [`docs/health/README.md`](docs/health/README.md).
