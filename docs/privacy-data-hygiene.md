# Data Privacy and Hygiene

Provider sources checked: 2026-09-19. Account settings were not inspected.

Training permission, retention, deletion, and access are separate controls.
Turning off model improvement does not remove stored chats or prevent all
safety review. Choose a service by the actual account terms, features, connected
tools, and data involved; a consumer subscription, API key, or local model alone
does not establish a complete privacy boundary.

## Provider controls

### Anthropic

Review Model Improvement in Claude's Privacy settings. Consumer terms cover
Free, Pro, Max, and Claude Code used through those accounts. Training can follow
consent, feedback, or safety review; do not assume every consumer account has
the same consent state. Feedback can include the related conversation.
[Anthropic training policy](https://privacy.claude.com/en/articles/10023580-is-my-data-used-for-model-training)

Deleting a chat normally removes it from backend storage within 30 days.
Consented training data may remain de-identified for up to five years. Turning
off improvement excludes previous and new chats from future training, but does
not reverse training already running or completed. Legal, dispute, safety, and
feedback retention exceptions apply. These consumer rules do not describe
Claude for Work or API retention.
[Anthropic retention policy](https://privacy.claude.com/en/articles/10023548-how-long-do-you-store-my-data)

### OpenAI

In ChatGPT Settings, open Data Controls and turn off **Improve the model for
everyone**. This covers new ChatGPT conversations and Codex tasks on personal
plans. Codex has a separate full-environment training setting to review.
Temporary Chats avoid history, memory creation, and model training, but can be
reviewed for abuse and are retained for 30 days under the documented policy.
[OpenAI Data Controls FAQ](https://help.openai.com/en/articles/7730893-chatgpt-data-usage-for-model-training)

API data is not used for model training unless explicitly shared. Abuse logs
normally last up to 30 days, with legal and safety exceptions. Application
state has separate retention that varies by endpoint. Approved Zero Data
Retention has endpoint, feature, and safety limitations; it is not a promise
that every API feature stores nothing. Check the endpoint table before relying
on it, and assess third-party tools separately.
[OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data)

### Google Gemini

Turn off **Keep Activity** in Gemini Apps Activity and review connected apps.
Future chats then avoid model improvement unless feedback is submitted, but
remain associated with the account for 72 hours. Human review can still support
safety. Previously reviewed chats are disconnected from the account and may
remain for up to three years; deleting activity does not delete those copies
or data held by other connected services. Workspace accounts have separate
terms, so verify the actual account rather than applying consumer rules to it.
[Gemini Apps Privacy Hub](https://support.google.com/gemini/answer/13594961)

### GitHub Copilot

Review AI training under Privacy in [Copilot settings](https://github.com/settings/copilot/features).
The April 24, 2026 policy allows training from Free, Pro, and Pro+ interaction
data unless opted out; previous opt-outs are preserved. Private repository
content sent as context can be interaction data, even though private repository
content at rest is excluded. Business and Enterprise accounts are outside this
consumer policy change.
[GitHub policy announcement](https://github.blog/changelog/2026-03-25-updates-to-our-privacy-statement-and-terms-of-service-how-we-use-your-data/)

## Local inference acceptance

The recorded [local stack](local-llm-stack.md) uses oMLX over loopback. Model
generation, tool calls, structured output, software-offline inference, and
failure when the local provider is unavailable have passed. The physical
network-disconnect test remains open. Operational accuracy supports supervised
assistance; autonomous writes remain outside the accepted use.

Before treating a workflow as local:

1. Confirm that the selected model and endpoint are local and cloud fallback
   is disabled.
2. Disconnect external networking and repeat representative inference with
   already-downloaded weights. Confirm provider failure does not trigger a
   remote model.
3. Review each agent tool, connector, extension, and telemetry setting. A local
   model can still call a tool that sends content elsewhere. Offline success
   proves offline operation is possible, not that online operation never sends
   data.
4. Locate transcripts, caches, exports, and backups. Confirm their access and
   synchronization settings independently of the model endpoint.

## Host hygiene

- Keep FileVault enabled and lock the session when unattended. Disk encryption
  protects a powered-off device; it does not isolate an unlocked session from
  software running as the same user.
- Use encrypted backups and test recovery. Include backup destinations and
  retention in the privacy review instead of avoiding backups entirely.
- Review agent transcript and cache locations before deleting anything. Cloud
  deletion does not remove local copies; local deletion does not remove cloud
  copies or backups. Do not assume local transcripts are kept forever or
  automatically removed without checking the installed client's settings.
- Inspect privacy, telemetry, file-context, and connected-app settings in each
  editor and assistant. On-device and cloud processing vary by feature.
- Keep credentials out of prompts, transcripts, shell history, and source
  control. Use the [credential lifecycle](credentials.md) for host secrets.

Inventory any existing Claude project transcripts without reading their contents:

```bash
if [ -d "$HOME/.claude/projects" ]; then
    du -sh "$HOME/.claude/projects"
    find "$HOME/.claude/projects" -type f -name '*.jsonl' -print
fi
```

Before cleanup, preserve needed work, select exact files, and check what the
client needs for session recovery. Provider controls should be rechecked when
the account, plan, feature, or policy changes; this page is a dated reference,
not verification of current account settings.
