/**
 * consult — second-opinion command for Pi
 *
 * /consult <question> asks a separate local agent CLI for a read-only second
 * opinion. It is intentionally narrow: no edits, no repo mutation, concise
 * disagreement/risk/recommendation output. This replaces the cryptic external
 * "oracle" idea with repo-owned terminology and guardrails.
 *
 * Default backend: Claude Code print mode, because Pi's default provider is
 * currently OpenAI/Codex. Use /consult --codex <question> when running Pi on a
 * Claude model and you want the opposite direction.
 *
 * Optional settings (~/.pi/agent/settings.json):
 *   { "consult": { "provider": "claude" | "codex", "timeoutMs": 120000 } }
 */

import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

type Provider = "claude" | "codex";

interface ConsultSettings {
  provider?: Provider;
  timeoutMs?: number;
}

const DEFAULT_PROVIDER: Provider = "claude";
const DEFAULT_TIMEOUT_MS = 120_000;
const MAX_NOTIFY_CHARS = 6000;

function getSettings(ctx: ExtensionContext): Required<ConsultSettings> {
  const settings = (ctx as any).settingsManager?.getSettings?.() ?? {};
  const consult = (settings.consult ?? {}) as ConsultSettings;
  const provider = consult.provider === "codex" || consult.provider === "claude" ? consult.provider : DEFAULT_PROVIDER;
  const timeoutMs = Number.isFinite(consult.timeoutMs) && Number(consult.timeoutMs) > 0
    ? Number(consult.timeoutMs)
    : DEFAULT_TIMEOUT_MS;
  return { provider, timeoutMs };
}

function parseArgs(raw: string, fallback: Provider): { provider: Provider; question: string } {
  const parts = raw.trim().split(/\s+/).filter(Boolean);
  let provider = fallback;
  const rest: string[] = [];

  for (const part of parts) {
    if (part === "--claude") {
      provider = "claude";
      continue;
    }
    if (part === "--codex") {
      provider = "codex";
      continue;
    }
    rest.push(part);
  }

  return { provider, question: rest.join(" ").trim() };
}

function consultPrompt(question: string, cwd: string): string {
  return `You are a second-opinion reviewer consulted from another coding agent.

Context:
- Working directory: ${cwd}
- You are not the primary implementer.
- Do not edit files.
- Do not mutate git, install dependencies, deploy, or run state-changing commands.
- If you inspect anything, stay read-only.

Task:
${question}

Return a concise consultation with these headings:
1. Agreement / disagreement
2. Risks or blind spots
3. Better terminology or framing, if any
4. Recommendation

Be direct. If the prompt lacks enough context, say what is missing instead of inventing facts.`;
}

function truncate(text: string): string {
  const clean = text.trim();
  if (clean.length <= MAX_NOTIFY_CHARS) return clean;
  return `${clean.slice(0, MAX_NOTIFY_CHARS)}\n\n… truncated; rerun with a narrower question if needed.`;
}

async function runClaude(pi: ExtensionAPI, ctx: ExtensionContext, prompt: string, timeoutMs: number) {
  return pi.exec(
    "claude",
    [
      "-p",
      "--no-session-persistence",
      "--permission-mode",
      "plan",
      "--tools",
      "",
      "--max-budget-usd",
      "0.50",
      prompt,
    ],
    { cwd: ctx.cwd, timeout: timeoutMs },
  );
}

async function runCodex(pi: ExtensionAPI, ctx: ExtensionContext, prompt: string, timeoutMs: number) {
  return pi.exec(
    "codex",
    ["exec", "--ephemeral", "--sandbox", "read-only", "-C", ctx.cwd, prompt],
    { cwd: ctx.cwd, timeout: timeoutMs },
  );
}

export default function (pi: ExtensionAPI) {
  pi.registerCommand("consult", {
    description: "Ask Claude/Codex for a read-only second opinion: /consult [--claude|--codex] <question>",
    handler: async (args, ctx) => {
      const settings = getSettings(ctx);
      const { provider, question } = parseArgs(args, settings.provider);

      if (!question) {
        ctx.ui.notify(
          "Usage: /consult [--claude|--codex] <question>\nExample: /consult challenge this implementation plan",
          "warning",
        );
        return;
      }

      ctx.ui.notify(`Consulting ${provider}…`, "info");
      const prompt = consultPrompt(question, ctx.cwd);
      const result = provider === "claude"
        ? await runClaude(pi, ctx, prompt, settings.timeoutMs)
        : await runCodex(pi, ctx, prompt, settings.timeoutMs);

      if (result.code !== 0) {
        const details = truncate(result.stderr || result.stdout || "No output");
        ctx.ui.notify(`Consult failed (${provider})\n${details}`, "warning");
        return;
      }

      ctx.ui.notify(`Consultation (${provider})\n\n${truncate(result.stdout)}`, "info");
    },
  });
}
