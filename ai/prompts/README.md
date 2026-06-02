# Prompts

System-prompt **artifacts** — the source material for the system prompts and advisor personas we run in web chats (Gemini, Claude.ai) and agents. Not deployed into projects.

- `system-prompt-advisor.md`, `system-prompt-detailed.md` — system-prompt sources
- `gemini-chunks/` — system instructions chunked to fit Gemini saved-info (loaded by `dotfiles agent web-chat-instructions`)
- `references/` — expert-panel / advisor source material

Related: prompt *methodology* (how to write these) lives in [`docs/knowledge/prompting/`](../../docs/knowledge/prompting/); cadence audit prompts are in [`ai/audits/`](../audits/); the universal rule kernel is `ai/agents/shared/rules.md`; skills in `ai/skills/`.
