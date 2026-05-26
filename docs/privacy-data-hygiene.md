# Data Privacy & Hygiene

Last updated: 2026-05-25

> Default-deny posture on AI training and scraping of private/personal content. Two separate risks to manage: (1) training use - your data improving someone's model - and (2) retention/exposure - your data sitting on their servers (or your disk) to be breached, subpoenaed, or reviewed. Different controls fix each. This doc is the practical playbook across the tools used in this setup.

Companion docs: [lm-studio-local-models.md](./lm-studio-local-models.md) (the local tier) and [pi-power-setup.md](./pi-power-setup.md) (local-first agent).

---

## Where does your data go? (the mental model)

Three tiers, by how far your prompt travels:

1. **On-device only** - LM Studio, and Pi when pointed at `lm-studio`. Prompts never leave the machine. No training, no retention, no breach surface beyond your own disk. This is the tier for anything genuinely sensitive.
2. **Cloud consumer** (ChatGPT, Gemini, Claude Free/Pro/Max) - trained on by default unless you opt out, multi-year retention if you don't. The toggles below exist precisely because the default is "yes, use my data."
3. **Cloud commercial / API** (Anthropic API, OpenAI API/Business/Enterprise, Workspace, GitHub Business/Enterprise) - not trained on by default, short retention (about 30 days), zero-data-retention (ZDR) available on request. Categorically better than consumer.

**Rule of thumb:** consumer plans are the dangerous default; API/commercial terms are safe-by-default; local is safest. Match the tier to the sensitivity.

---

## Provider-by-provider

### Anthropic - Claude & Claude Code
- **Opt out:** `claude.ai` -> Settings -> Privacy -> turn off the model-training toggle.
- **Plans:** Free/Pro/Max are consumer terms - toggle applies, and "coding sessions" (Claude Code) are explicitly covered. API / Claude for Work are commercial - never trained on.
- **Retention:** opted out -> 30 days backend, then purged. Opted in -> up to 5 years de-identified in training pipelines.
- **Claude Code specifics:** auth method decides the terms. Subscription login (`oauthAccount`, `organizationType: claude_max`) = consumer. API key = commercial. Check the account type, not the app.
- **The overlooked copy:** Claude Code writes full plaintext transcripts to `~/.claude/projects/<project>/*.jsonl` that persist forever locally regardless of server settings. See cleanup below.
- **Delete:** delete chats in-app -> removed from history, purged backend within 30 days; excluded from future training. Cannot un-train completed runs.

### OpenAI - ChatGPT & API
- **Opt out:** Profile -> Settings -> Data Controls -> turn off "Improve the model for everyone." Account-wide, forward-looking, immediate.
- **Ephemeral option:** use Temporary Chat for one-offs (not saved to history, not trained on). The Memory feature persists data across chats - review/clear it.
- **API / Business / Enterprise:** not trained on by default; about 30-day retention; opt-in only. ZDR available for eligible use cases.
- **Delete:** Settings -> Data Controls -> clear conversations; deleted chats removed within 30 days.

### Google - Gemini & Workspace
- **Opt out:** `myaccount.google.com` -> Data & Privacy -> Gemini Apps Activity -> Turn off. Stops future conversations from human review and model training.
- **Sharp caveats (Gemini is the worst-behaved of the four):**
  - Even with activity off, chats are kept up to 72h "to provide the service."
  - Anything a human reviewer already saw is kept up to 3 years on a separate path with no user-facing delete. Treat anything you would regret a Google contractor reading as never safe to paste into consumer Gemini.
  - Default auto-delete is 18 months - shorten it (Gemini Apps Activity -> Auto-delete -> 3 months).
  - Personal Intelligence dashboard (in the Gemini UI) controls which Google services (Gmail, Drive, Calendar, Maps) Gemini can read - audit it.
- **Workspace (paid):** content is not used to train models under Workspace terms - different from consumer Gmail/Gemini.

### GitHub - Copilot
- **Opt out:** `github.com/settings/copilot/features` -> Privacy -> turn off "Allow GitHub to use my data for AI model training." Account-wide (one switch covers all repos).
- **Default changed Apr 24, 2026:** GitHub now defaults this ON for Copilot Free/Pro/Pro+, using interaction data (prompts, suggestions, code snippets sent as context - including from private repos while you code). Business/Enterprise are exempt by contract.
- **Private repos at rest are NOT trained on** - never were. The exposure is only the live Copilot interaction data, and only if you use Copilot.

---

## Settings to turn OFF (consolidated checklist)

- [ ] Claude: Privacy -> model training off
- [ ] ChatGPT: Data Controls -> "Improve the model for everyone" off; review/clear Memory
- [ ] Gemini: Gemini Apps Activity off; Auto-delete -> 3 months; audit Personal Intelligence connections
- [ ] GitHub: Copilot features -> training off
- [ ] Any AI IDE (Cursor/Windsurf/Zed AI): enable Privacy Mode / disable telemetry & code snippet collection
- [ ] OS: keep FileVault (or equivalent full-disk encryption) on - the backstop for every local plaintext transcript

---

## The local tier - LM Studio + Pi (the safe default for sensitive work)

**LM Studio** runs inference fully on-device. Prompts never leave the machine, so no training, no retention, no third party. This is the tier for genuinely sensitive content. See [lm-studio-local-models.md](./lm-studio-local-models.md) for model choices.

**Hygiene standard for "is this actually private?":**
- Confirm LM Studio is running the local server / local model, not a remote/proxy provider. The whole guarantee is that nothing leaves the machine - verify that's true before trusting it with sensitive input.
- LM Studio can run fully offline - a hard test is to pull the network and confirm inference still works. Disable any update/telemetry checks in its settings.
- Model downloads come from Hugging Face (weights coming in, not your data going out) - fine. Your prompts and the model's outputs stay local.
- Local does not mean immortal-safe: the only remaining surface is your disk, so full-disk encryption plus not syncing the chat store to cloud backup is what closes the loop.

**Pi** is local-first as configured here (`defaultProvider: lm-studio`), but it is not automatically private:
- Provider/model swap mid-session can route your prompt to any of 40+ cloud providers. The moment you swap to a cloud model, you are back in cloud-consumer/API territory.
- The `oracle` extension (on the eval list) deliberately consults cloud Claude/Codex for a second opinion - that exfiltrates context by design.
- Recommended: add the `filter-output` / `security` extension (michalvavra/agents) to redact tokens/secrets from tool output, and keep the `lm-studio` provider as the default for any sensitive repo.
- `safe-git` gates destructive git ops, not data egress - don't mistake it for a privacy control.

---

## Other tools & gotchas (anything that sends data away)

- **Claude Code local transcripts** - `~/.claude/projects/<project>/*.jsonl`, full plaintext, forever. The single most overlooked copy. Scrub periodically (below).
- **AI IDEs** (Cursor, Windsurf, Zed AI, Copilot in editors) - each sends file context to a cloud model. Look for a Privacy Mode (Cursor's, when on, means code is not stored/trained) and disable telemetry.
- **Apple Intelligence / Siri, browser AI sidebars, AI keyboards, meeting transcribers** - all ship content off-device. Each has its own data-use setting; treat anything pasted into them as "left the building."
- **Vetting framework - 5 questions for any new tool:**
  1. Does it send my input off-device? (If no, done - it's the local tier.)
  2. Where does it go - which company, which plan tier, which region/sub-processors?
  3. Is it trained on by default? (Consumer = usually yes; API/commercial = usually no.)
  4. What is the retention, and is there a delete that actually purges?
  5. Is there an opt-out / ZDR / local mode? Set it before first real use.

---

## How to tell a provider "don't touch my data"

- **Consumer plans:** flip the training toggle off (per-provider above). That is the only lever, and it is forward-looking, never retroactive.
- **API / commercial:** you are opted out of training by default; for retention, request a Zero Data Retention (ZDR) agreement (Anthropic, OpenAI both offer it for eligible use). ZDR = prompts not logged at all.
- **The strongest signal is tier choice:** running sensitive work on an API key under commercial terms (or locally) tells them far more than any toggle - there is simply nothing to train on.

---

## Periodic cleanup

**Cloud chats:** delete in-app per provider (above). Remember: deletion excludes from future training and triggers backend purge (about 30 days), but cannot pull data out of a completed training run, and (Gemini) cannot remove human-reviewed chats.

**Local Claude Code transcripts** - inventory, then targeted delete with a dry-run first:

```bash
# Inventory: sessions per project, size, date range
find ~/.claude/projects -maxdepth 1 -mindepth 1 -type d | while read -r d; do
  cnt=$(find "$d" -name '*.jsonl' | wc -l | tr -d ' '); [ "$cnt" -eq 0 ] && continue
  printf '%4s  %6s  %s\n' "$cnt" "$(du -sh "$d" | cut -f1)" "$(basename "$d")"
done | sort -rn

# DRY RUN - list what a pattern would remove (no deletion)
find ~/.claude/projects -maxdepth 1 -type d -name '*<project>*'

# DELETE - only after eyeballing the dry run
find ~/.claude/projects -maxdepth 1 -type d -name '*<project>*' -exec rm -rf {} +
```

**Before deleting**, mine dead projects for durable insights worth crystallizing into a repo/wiki/note - once the transcript and repo are both gone, that thinking is unrecoverable.

---

## The real backstop: local-disk hygiene

Toggles stop training. They do nothing for the plaintext piling up on your own disk. What protects that:

- **Full-disk encryption (FileVault):** keep it on. A lost/stolen machine becomes a non-event. This is higher-leverage than any chat scrub.
- **Backups are a tradeoff:** no backup is privacy-good (nothing replicated to a backup set or to iCloud) but a data-loss risk (a dead SSD loses everything). The privacy-respecting fix is an encrypted, self-controlled backup (encrypted external drive via Time Machine, or `restic`/Arq to a destination you hold the key to) - not iCloud/Drive sync of `~/.claude` or code dirs.

---

## Sources

- [Anthropic - Updates to Consumer Terms](https://www.anthropic.com/news/updates-to-our-consumer-terms) and [retention](https://privacy.claude.com/en/articles/10023548-how-long-do-you-store-my-data)
- [OpenAI - turn off model training](https://help.openai.com/en/articles/8983082-how-do-i-turn-off-model-training-to-stop-openai-training-models-on-my-conversations) and [how data is used](https://openai.com/policies/how-your-data-is-used-to-improve-model-performance/)
- [Google - Gemini Apps Privacy Hub](https://support.google.com/gemini/answer/13594961) and [Workspace Gen-AI Privacy Hub](https://knowledge.workspace.google.com/admin/gemini/generative-ai-in-google-workspace-privacy-hub)
- [GitHub - Privacy/ToS update Apr 2026](https://github.blog/changelog/2026-03-25-updates-to-our-privacy-statement-and-terms-of-service-how-we-use-your-data/) and [community FAQ](https://github.com/orgs/community/discussions/188488)
