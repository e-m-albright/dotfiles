# Pi Best-in-Class Setup Implementation Plan

> **REQUIRED SUB-SKILL:** Use the executing-plans skill to implement this plan task-by-task.

**Goal:** Make the base Pi setup feel comparable to or better than Claude Code and Codex CLI for Evan's workflow, without losing Pi's small-core advantage.

**Architecture:** Keep base Pi as the fleet slot and add only high-leverage, low-prompt-cost capabilities. Prefer hook/event extensions and shared skills over always-on tools. Vendor tiny, security-sensitive extensions in `agents/pi/extensions/` so they are reviewable and version-controlled.

**Tech Stack:** Pi coding agent (`@earendil-works/pi-coding-agent`), TypeScript Pi extensions, `pi-superpowers-plus`, `mitsupi`, shared `.ai/skills`, shared `AGENTS.md`, dotfiles Bash setup scripts.

---

## Research Context

### Current repo state

Pi is managed in `agents/pi/` and documented in `docs/pi-power-setup.md`.

Current files:

- `agents/pi/settings.json`
- `agents/pi/models.json`
- `agents/pi/setup.sh`
- `agents/pi/extensions/safe-git.ts`
- `agents/pi/extensions/git-status.ts`

Current package set:

- `pi-superpowers-plus`: Superpowers-style TDD, verification, and subagent workflow.
- `mitsupi`: Armin Ronacher's package with review, answer, todos, handoff, loop, notify, browser, tmux, GitHub, Sentry, native web search, uv, and related skills/extensions.

Current vendored extensions:

- `safe-git.ts`: Approval gate for dangerous `git` and `gh` commands.
- `git-status.ts`: Footer/status integration for git, context, quota, and cost.

Current model posture:

- `agents/pi/settings.json` currently defaults to `openai-codex` / `gpt-5.5`.
- `agents/pi/models.json` still defines LM Studio local models, including Qwen 3.6 35B-A3B and Gemma 4 E4B.

Important setup invariant:

- Pi reads shared skills from `~/.agents/skills`.
- Pi reads baked global rules from `~/.pi/agent/AGENTS.md`.
- Subagents are deployed into `~/.pi/agent/agents`.
- This makes Pi part of the same fleet as Claude Code, Cursor, and Codex instead of a separate one-off tool.

### Official Pi direction

Primary source: `https://github.com/earendil-works/pi`

The original Pi direction is not to ship a giant batteries-included agent. The official README frames Pi as:

- A minimal terminal coding harness.
- Four default tools: read, write, edit, bash.
- Extensible through TypeScript extensions, skills, prompt templates, themes, and packages.
- A harness that intentionally skips things like subagents and plan mode in core, because users can add those through packages.
- A tool that supports interactive mode, print/JSON mode, RPC mode, and SDK embedding.

Relevant official recommendation:

- Adapt Pi to your workflows, not the other way around.
- Use packages for reusable behavior.
- Treat packages as trusted code because extensions run with full system access.
- Share OSS session traces with `pi-share-hf` if working on public OSS and willing to contribute traces for model/tool evaluation.

Implication for this plan:

- Do not make our base Pi resemble oh-my-pi by adding many built-in tools.
- Do add a small number of local, reviewable extensions that close safety and workflow gaps.

### Community recommendations

Primary source: `https://github.com/qualisero/awesome-pi-agent`

Community extensions cluster into these categories:

1. Safety and permissions
   - `safe-git` from `qualisero/rhubarb-pi`
   - `filter-output` and `security` from `michalvavra/agents`
   - `permission` from `prateekmedia/pi-hooks`
   - `toolwatch` from `kcosr/pi-extensions`

2. Workflow bundles
   - `mitsupi` from `mitsuhiko/agent-stuff`
   - `pi-superpowers-plus`
   - handoff, review, todos, answer, loop, notify style extensions

3. Model and quota helpers
   - `oracle` from `hjanuschka/shitty-extensions`
   - `usage-bar`, `status-widget`, `cost-tracker`
   - `pi-powerline-footer`

4. Code intelligence and heavy harness features
   - LSP extensions
   - SCIP code intelligence
   - DAP/debugger-like approaches

5. Sandboxing and orchestration
   - `nono`
   - `gondolin`
   - `lima`
   - `task-factory`
   - `PiSwarm`

Implication for this plan:

- The best lean setup should pull from categories 1 through 3.
- Categories 4 and 5 should stay optional until there is a recurring failure mode.

### Armin Ronacher's package: `mitsupi`

Primary source: `https://github.com/mitsuhiko/agent-stuff`

`mitsupi` already covers many quality-of-life and workflow features:

Skills include:

- `/commit`
- `/github`
- `/native-web-search`
- `/summarize`
- `/tmux`
- `/sentry`
- `/uv`
- `/web-browser`
- `/librarian`
- `/pi-share`
- `/mermaid`
- others, including personal/local Austrian transport helpers

Extensions include:

- `answer.ts`: answer questions one at a time in a TUI.
- `btw.ts`: side-chat popover.
- `control.ts`: session control helpers.
- `files.ts`: file browser.
- `split-fork.ts`: branch current session into a new Pi process in a Ghostty split.
- `loop.ts`: iterative prompt loop.
- `multi-edit.ts`: batch multi edits and patch support.
- `notify.ts`: native desktop notifications.
- `prompt-editor.ts`: prompt mode selector.
- `review.ts`: code review command.
- `session-breakdown.ts`: session and cost analysis.
- `todos.ts`: file-backed todo manager.
- `uv.ts`: uv helpers.
- `whimsical.ts`: alternate thinking text.

Implication for this plan:

- Do not duplicate `mitsupi` features unless the local version is specifically safer, lighter, or more integrated with this dotfiles repo.
- Current setup is already stronger than a stock Pi install because `mitsupi` supplies the daily workflow surface.

### `shitty-extensions` candidates

Primary source: `https://github.com/hjanuschka/shitty-extensions`

Relevant extensions:

- `oracle.ts`: Second opinion from another model without switching contexts. Supports model picker, file inclusion, context inheritance, and optional injection of the oracle answer into the main conversation.
- `plan-mode.ts`: Claude Code-style read-only exploration mode with `/plan` and `--plan`.
- `memory-mode.ts`: Writes instructions into AGENTS files through `/mem` or `/remember`.
- `handoff.ts`: Transfers context to a new focused session.
- `usage-bar.ts`: Provider usage statistics and reset countdowns.
- `status-widget.ts`: Provider status in the footer.
- `cost-tracker.ts`: Spending analysis from Pi logs.

Implication for this plan:

- Cherry-pick `oracle.ts` and `plan-mode.ts` if license and implementation review look good.
- Do not install the full package by default because it includes novelty and overlapping features.
- Avoid `memory-mode.ts` by default because this repo intentionally keeps curated memory in version-controlled docs and ADRs, not ad hoc tool memory.
- Avoid `handoff.ts` unless it beats the already-installed `mitsupi` handoff behavior.
- Avoid `usage-bar.ts`, `status-widget.ts`, and `cost-tracker.ts` if the same signal can be folded into our custom `git-status.ts`.

### oh-my-pi research summary

Primary source: `https://github.com/can1357/oh-my-pi`

oh-my-pi is a fork/rewrite that adds a large battery-included harness:

- 32 built-in tools.
- 40+ providers.
- 14 search backends.
- 13 LSP operations.
- 27 DAP operations.
- Rust core components.
- Hashline editing with stale-anchor recovery.
- Persistent Python and Bun/JS execution kernels.
- Browser and Electron automation.
- Schema-validated subagents.
- Config import from multiple agent/editor ecosystems.

Standing decision:

- Keep base Pi as the fleet slot.
- Install or evaluate oh-my-pi side-by-side only if there is a specific heavy refactor, LSP, DAP, browser automation, or hashline-editing need.

Why:

- oh-my-pi abandons Pi's minimalism on purpose.
- It uses its own `~/.omp` namespace and does not fit the repo's shared `~/.agents/skills` plus `AGENTS.md` model.
- It has higher churn and a larger prompt/tool surface.

### Best-in-class target

The target is not to clone Claude Code or Codex CLI. The target is to make Pi the owner-controlled harness:

| Capability | Current state | Target state |
|---|---|---|
| Shared rules and skills | Strong | Keep |
| Subagents | Strong via `pi-superpowers-plus` | Keep |
| Review, todos, loop, handoff | Strong via `mitsupi` | Keep |
| Dangerous git protection | Present via `safe-git` | Keep and smoke test |
| Dangerous bash protection | Gap | Add `security.ts` |
| Secret redaction | Gap | Add `filter-output.ts` |
| Plan/read-only mode | Mostly process-only | Add `plan-mode.ts` |
| Second opinion | Manual model switch today | Add `oracle.ts` |
| Provider/quota visibility | Partial via footer | Extend `git-status.ts` instead of adding multiple packages |
| Heavy code intelligence | Not installed | Defer |
| OS sandbox | Not installed | Defer |

Recommended default final set:

- Packages:
  - `pi-superpowers-plus`
  - `mitsupi`
- Vendored extensions:
  - `safe-git.ts`
  - `git-status.ts`
  - `security.ts`
  - `filter-output.ts`
  - `oracle.ts`
  - `plan-mode.ts`

Explicit non-goals:

- Do not install oh-my-pi as the default Pi.
- Do not add MCP adapter support unless ADR-0005 is revised.
- Do not add `nono`, `gondolin`, or `lima` by default.
- Do not install full extension bundles when only one or two files are needed.
- Do not add a second permission framework if `safe-git` plus `security.ts` covers the risk.
- Do not add memory-writing commands that bypass the repo's docs and ADR discipline.

---

## Implementation Plan

### Task 1: Re-read source docs and confirm candidate licenses

**TDD scenario:** Research and review task. No code test. Verification is source capture and license confirmation.

**Files:**

- Read: `docs/pi-power-setup.md`
- Read: `docs/adr/0005-re-add-pi-as-local-first-agent.md`
- Read: `docs/adr/0006-pi-power-packages-mitsupi-and-safe-git.md`
- Read: `agents/pi/settings.json`
- Read: `agents/pi/setup.sh`
- Read: remote `michalvavra/agents` extension files
- Read: remote `hjanuschka/shitty-extensions` extension files

**Step 1: Confirm repo state**

Run:

```bash
git status --short --branch
```

Expected:

- Branch is intentional for this work.
- Any unrelated untracked files are not staged.

**Step 2: Review existing Pi docs and ADRs**

Read:

```text
docs/pi-power-setup.md
docs/adr/0005-re-add-pi-as-local-first-agent.md
docs/adr/0006-pi-power-packages-mitsupi-and-safe-git.md
```

Expected:

- ADR-0005 still says no MCP by default.
- ADR-0006 still approves `mitsupi` and `safe-git`.
- No newer ADR contradicts this plan.

**Step 3: Fetch candidate extension sources**

Use `librarian` or a temporary checkout under `~/.cache/checkouts` for:

```text
https://github.com/michalvavra/agents
https://github.com/hjanuschka/shitty-extensions
```

Expected:

- Source files are locally inspectable.
- LICENSE files are present and compatible with vendoring into this dotfiles repo.

**Step 4: Confirm exact source files**

Locate and inspect:

```text
michalvavra/agents: agents/pi/extensions/filter-output.ts
michalvavra/agents: agents/pi/extensions/security.ts
hjanuschka/shitty-extensions: extensions/oracle.ts
hjanuschka/shitty-extensions: extensions/plan-mode.ts
```

Expected:

- Each extension is small enough to vendor or can be trimmed safely.
- No extension performs unexpected network calls except where expected for `oracle`.
- No extension writes to project files unexpectedly.

**Step 5: Commit research checkpoint only if docs changed**

If any source notes are added to this plan or docs:

```bash
git add docs/plans/2026-05-29-pi-best-in-class-setup.md
git commit -m "docs(pi): plan best-in-class setup"
```

Expected:

- Only documentation is committed.

### Task 2: Vendor `filter-output.ts`

**TDD scenario:** New safety feature. Write or run smoke checks around redaction behavior before trusting it.

**Files:**

- Create: `agents/pi/extensions/filter-output.ts`
- Modify: `docs/pi-power-setup.md`

**Step 1: Copy the extension into the repo**

Copy from the reviewed upstream source into:

```text
agents/pi/extensions/filter-output.ts
```

Preserve attribution in file comments if upstream includes it. If upstream has no attribution header, add a short comment naming upstream URL, commit SHA, license, and port date.

**Step 2: Inspect for secrets patterns and false positives**

Confirm the extension redacts common patterns:

- API keys
- bearer tokens
- GitHub tokens
- OpenAI/Anthropic-style keys
- password-like values
- `.env`-style assignments

Expected:

- Redaction happens before model-visible tool output.
- The extension does not mutate files.

**Step 3: Run TypeScript or Pi load smoke test**

Run the project's relevant Pi setup path:

```bash
agents/pi/setup.sh
```

Then open Pi and run:

```text
/reload
```

Expected:

- Pi starts without extension load errors.
- `/reload` succeeds.

**Step 4: Manual redaction smoke test**

In a disposable Pi session, ask Pi to run a command that prints fake secrets:

```bash
printf 'OPENAI_API_KEY=sk-test1234567890\nGITHUB_TOKEN=ghp_test1234567890\npassword=hunter2\n'
```

Expected:

- Tool output shown to the model/user redacts sensitive values.
- Fake secret values do not appear in the assistant's visible context.

**Step 5: Update docs**

Add `filter-output.ts` to the `Packages & extensions we run` table in:

```text
docs/pi-power-setup.md
```

Expected:

- Docs explain this is a hook/event safety extension, not a new model tool.

**Step 6: Commit**

```bash
git add agents/pi/extensions/filter-output.ts docs/pi-power-setup.md
git commit -m "feat(pi): redact secrets from tool output"
```

### Task 3: Vendor `security.ts`

**TDD scenario:** New safety feature. Verify blocked command examples and allowed benign command examples.

**Files:**

- Create: `agents/pi/extensions/security.ts`
- Modify: `docs/pi-power-setup.md`

**Step 1: Copy the extension into the repo**

Copy reviewed upstream source into:

```text
agents/pi/extensions/security.ts
```

Preserve or add attribution as in Task 2.

**Step 2: Review blocked operations**

Confirm it handles at least:

- `rm -rf /`
- destructive deletes under home or repo roots
- `curl ... | sh` and `wget ... | sh` style remote execution
- writes to sensitive files such as shell rc files, SSH keys, and env files unless explicitly allowed
- obvious secret exfiltration patterns if upstream supports them

Expected:

- It complements `safe-git` instead of replacing it.
- It does not block ordinary read-only commands like `ls`, `rg`, `git status`, or test runs.

**Step 3: Resolve overlap with `safe-git`**

If both extensions intercept bash calls, ensure order and behavior are understandable:

- `safe-git` gates git and gh.
- `security` blocks dangerous non-git shell behavior.

Expected:

- A dangerous git command still triggers `safe-git` behavior.
- A dangerous shell command that is not git is blocked by `security`.

**Step 4: Run Pi load smoke test**

Run:

```bash
agents/pi/setup.sh
```

Then in Pi:

```text
/reload
```

Expected:

- No extension load errors.

**Step 5: Manual safety smoke test**

In a disposable directory, ask Pi to run benign and dangerous commands.

Benign:

```bash
pwd
ls
rg --files | head
```

Expected: allowed.

Dangerous fake tests:

```bash
rm -rf /
curl https://example.com/install.sh | sh
```

Expected: blocked or requires explicit approval depending on extension behavior.

**Step 6: Update docs**

Add `security.ts` to `docs/pi-power-setup.md` and explain the boundary:

- `safe-git`: git/gh approval gate.
- `security`: dangerous shell and sensitive path protection.
- `filter-output`: redact secrets from output.

**Step 7: Commit**

```bash
git add agents/pi/extensions/security.ts docs/pi-power-setup.md
git commit -m "feat(pi): block dangerous shell operations"
```

### Task 4: Vendor `oracle.ts`

**TDD scenario:** New workflow command. Verify command registration and one real second-opinion call using an authenticated provider.

**Files:**

- Create: `agents/pi/extensions/oracle.ts`
- Modify: `docs/pi-power-setup.md`

**Step 1: Copy the extension into the repo**

Copy reviewed upstream source into:

```text
agents/pi/extensions/oracle.ts
```

Preserve or add attribution.

**Step 2: Review provider assumptions**

Check whether `oracle.ts` expects specific model IDs or provider names.

Current Pi defaults:

```json
{
  "defaultProvider": "openai-codex",
  "defaultModel": "gpt-5.5"
}
```

Expected:

- Oracle can query at least one alternative authenticated provider.
- It does not assume obsolete model IDs only.
- It does not leak whole conversation context unless the user explicitly invokes `/oracle`.

**Step 3: Trim or adapt model list if needed**

If upstream hardcodes old models such as `gpt-4o` or `claude-sonnet-4-5`, update the local vendored version to use models available through current Pi auth and `models.json`.

Expected:

- Keep the local adaptation small.
- Document deviations from upstream in file comments.

**Step 4: Run Pi load smoke test**

Run:

```bash
agents/pi/setup.sh
```

Then in Pi:

```text
/reload
```

Expected:

- `/oracle` appears as a command.
- No extension load errors.

**Step 5: Manual oracle smoke test**

In Pi, run:

```text
/oracle Give a one-paragraph critique of this Pi setup plan. Focus on what to remove.
```

Expected:

- Model picker appears or a configured model is used.
- The answer can be kept out of or inserted into context according to extension behavior.
- No unexpected file writes occur.

**Step 6: Update docs**

Add `oracle.ts` to `docs/pi-power-setup.md` and explain intended use:

- Architecture second opinions.
- Hard bug hypotheses.
- Review before committing.
- Not for routine every-turn use.

**Step 7: Commit**

```bash
git add agents/pi/extensions/oracle.ts docs/pi-power-setup.md
git commit -m "feat(pi): add second-opinion oracle command"
```

### Task 5: Vendor `plan-mode.ts`

**TDD scenario:** New safety/workflow mode. Verify read-only exploration blocks writes and still allows reading/searching.

**Files:**

- Create: `agents/pi/extensions/plan-mode.ts`
- Modify: `docs/pi-power-setup.md`

**Step 1: Copy the extension into the repo**

Copy reviewed upstream source into:

```text
agents/pi/extensions/plan-mode.ts
```

Preserve or add attribution.

**Step 2: Review enforcement boundary**

Confirm whether plan mode is:

- Prompt-only guidance.
- Tool-level enforcement.
- A mix of both.

Expected:

- Prefer tool-level enforcement for write/edit/bash mutation if available.
- If prompt-only, document the limitation clearly.

**Step 3: Check interaction with process rules**

This repo already has strong planning rules and brainstorming/writing-plans skills.

Expected:

- `plan-mode.ts` should complement those rules by adding a harness-level read-only toggle.
- It should not replace the writing-plans skill or docs/plans process.

**Step 4: Run Pi load smoke test**

Run:

```bash
agents/pi/setup.sh
```

Then in Pi:

```text
/reload
/plan
```

Expected:

- `/plan` toggles mode.
- No extension load errors.

**Step 5: Manual read-only smoke test**

In plan mode, ask Pi to:

```text
Read agents/pi/settings.json and propose one improvement, but do not edit files.
```

Expected:

- Reads are allowed.
- No files are modified.

Then ask Pi to edit a file while plan mode is on.

Expected:

- Edit is blocked or the model refuses due to plan mode.

**Step 6: Update docs**

Add `plan-mode.ts` to `docs/pi-power-setup.md` and document when to use it:

- Researching unfamiliar code.
- Reviewing PRs.
- Planning before implementation.
- Letting a model inspect risky repos without modifying files.

**Step 7: Commit**

```bash
git add agents/pi/extensions/plan-mode.ts docs/pi-power-setup.md
git commit -m "feat(pi): add read-only plan mode"
```

### Task 6: Improve `git-status.ts` into the single status surface

**TDD scenario:** Modify existing extension. Run existing behavior first, then add one status signal at a time with smoke checks.

**Files:**

- Modify: `agents/pi/extensions/git-status.ts`
- Modify: `docs/pi-power-setup.md`

**Step 1: Capture current behavior**

Open Pi in this repo and note the existing footer/status values.

Expected current values may include:

- Git branch.
- Context usage.
- Quota/cost where available.

**Step 2: Decide exact status fields**

Target fields:

- Current git branch.
- Dirty state.
- Provider/model.
- Context usage.
- Cost.
- Optional quota/reset information if Pi exposes it cleanly.

Non-goal:

- Do not add a large external status package if `git-status.ts` can display the useful parts.

**Step 3: Add one field at a time**

Modify `agents/pi/extensions/git-status.ts` in small increments.

Suggested order:

1. Provider/model.
2. Dirty state.
3. Context/cost formatting cleanup.
4. Optional quota/reset if exposed by Pi APIs.

After each increment, run:

```text
/reload
```

Expected:

- Footer renders without errors.
- No performance regression or visible flicker.

**Step 4: Avoid duplicating community packages**

Before adding quota logic, compare against:

- `usage-bar.ts`
- `status-widget.ts`
- `cost-tracker.ts`
- `pi-powerline-footer`

Expected:

- Implement only the subset that is small and stable.
- Defer if provider APIs are brittle or require too much code.

**Step 5: Update docs**

Update `docs/pi-power-setup.md` to say `git-status.ts` is the single local status surface and replaces the need for several status packages.

**Step 6: Commit**

```bash
git add agents/pi/extensions/git-status.ts docs/pi-power-setup.md
git commit -m "feat(pi): expand footer status surface"
```

### Task 7: Add an ADR for the final extension policy

**TDD scenario:** Documentation decision. Verification is consistency with existing ADR format.

**Files:**

- Create: `docs/adr/0007-pi-lean-power-setup.md` or next available ADR number.
- Modify: `docs/pi-power-setup.md`

**Step 1: Inspect existing ADR numbering**

Run:

```bash
ls docs/adr
```

Expected:

- Determine the next ADR number.

**Step 2: Write ADR**

The ADR should record:

- Decision: keep base Pi as the default fleet Pi.
- Decision: use `pi-superpowers-plus` and `mitsupi` as core packages.
- Decision: vendor small safety and workflow extensions.
- Decision: avoid full extension bundles by default.
- Decision: keep oh-my-pi side-by-side only for heavy IDE/debugger sessions.

**Step 3: Link ADR from Pi docs**

Update:

```text
docs/pi-power-setup.md
```

Expected:

- The practical doc links the new ADR.

**Step 4: Commit**

```bash
git add docs/adr/0007-pi-lean-power-setup.md docs/pi-power-setup.md
git commit -m "docs(pi): record lean power setup policy"
```

### Task 8: Run final verification

**TDD scenario:** Final integration verification.

**Files:**

- Verify: `agents/pi/extensions/*.ts`
- Verify: `agents/pi/setup.sh`
- Verify: `docs/pi-power-setup.md`

**Step 1: Run shell/script checks available in this repo**

Discover commands:

```bash
just --list
```

Run the relevant existing checks, likely one of:

```bash
just check
just ci
./bin/dotfiles doctor
```

Expected:

- Checks pass or failures are unrelated and documented.

**Step 2: Run Pi setup**

Run:

```bash
agents/pi/setup.sh
```

Expected:

- Settings and models symlink.
- AGENTS.md is baked.
- Subagents deploy.
- Extensions symlink.
- Packages are installed or skipped if already present.

**Step 3: Run Pi interactive smoke test**

Open Pi in this repo and run:

```text
/reload
/safegit-status
/plan
/oracle Critique this setup in one paragraph.
```

Expected:

- No extension load errors.
- Existing `safe-git` command still works.
- `/plan` works.
- `/oracle` works or reports a clear auth/config issue.

**Step 4: Run safety smoke tests**

Test fake secret output and dangerous shell examples as documented in Tasks 2 and 3.

Expected:

- Secrets redact.
- Dangerous shell commands block.
- Benign read-only commands still work.

**Step 5: Confirm git state**

Run:

```bash
git status --short --branch
git log --oneline -8
```

Expected:

- Only intentional commits exist.
- No unrelated files are staged.
- Any unrelated untracked files from other work remain untouched.

---

## Rollback Plan

Each extension is independently vendored and can be disabled by removing or renaming its file in `agents/pi/extensions/`, then running:

```bash
agents/pi/setup.sh
```

or reloading Pi:

```text
/reload
```

Rollback order if something breaks:

1. Disable `plan-mode.ts` if read/write behavior becomes confusing.
2. Disable `oracle.ts` if provider auth or model selection breaks sessions.
3. Disable `security.ts` if it blocks normal development commands too aggressively.
4. Disable `filter-output.ts` only if it corrupts outputs; otherwise keep it because secret redaction is high-value.
5. Keep `safe-git.ts` unless it is the direct source of a git workflow failure.

---

## Acceptance Criteria

The setup is complete when:

- `agents/pi/extensions/filter-output.ts` is vendored, documented, and smoke-tested.
- `agents/pi/extensions/security.ts` is vendored, documented, and smoke-tested.
- `agents/pi/extensions/oracle.ts` is vendored, documented, and smoke-tested.
- `agents/pi/extensions/plan-mode.ts` is vendored, documented, and smoke-tested.
- `agents/pi/extensions/git-status.ts` remains the single local status/footer surface.
- `docs/pi-power-setup.md` reflects the final setup and non-goals.
- A new ADR records the lean extension policy.
- Final verification output is captured in the implementing session.

---

## Later Evaluation Backlog

Do not implement these by default. Revisit only if there is a recurring need.

- oh-my-pi side-by-side install for heavy LSP/DAP/hashline sessions.
- SCIP or LSP code intelligence if current grep/read/edit workflows repeatedly fail on large refactors.
- `nono`, `gondolin`, or `lima` sandboxing if running untrusted repos or destructive automation becomes normal.
- `task-factory` or `PiSwarm` if queue-based multi-agent work becomes routine.
- `pi-share-hf` if publishing OSS session traces becomes desirable.
- MCP adapter only if ADR-0005 is explicitly revised.
