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
 * Adversarial backend: /consult --fable <question> routes to Claude Fable 5
 * (the strongest public model, June 2026) for a high-leverage second opinion.
 * It is pricier ($10/$50 per Mtok), so it stays opt-in behind the flag. Any
 * Claude model id can be forced with --model <id>. Note Fable 5 deflects some
 * cybersecurity/bio prompts to Opus 4.8 (<5% of sessions).
 *
 * Optional settings (~/.pi/agent/settings.json):
 *   { "consult": { "provider": "claude" | "codex", "model": "claude-fable-5",
 *                  "timeoutMs": 120000 } }
 */

import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

type Provider = "claude" | "codex";

interface ConsultSettings {
  provider?: Provider;
  model?: string;
  timeoutMs?: number;
}

const DEFAULT_PROVIDER: Provider = "claude";
const DEFAULT_TIMEOUT_MS = 120_000;
const MAX_NOTIFY_CHARS = 6000;
const FABLE_MODEL = "claude-fable-5";

function getSettings(ctx: ExtensionContext): Required<ConsultSettings> {
  const settings = (ctx as any).settingsManager?.getSettings?.() ?? {};
  const consult = (settings.consult ?? {}) as ConsultSettings;
  const provider = consult.provider === "codex" || consult.provider === "claude" ? consult.provider : DEFAULT_PROVIDER;
  const model = typeof consult.model === "string" && consult.model.trim() ? consult.model.trim() : "";
  const timeoutMs = Number.isFinite(consult.timeoutMs) && Number(consult.timeoutMs) > 0
    ? Number(consult.timeoutMs)
    : DEFAULT_TIMEOUT_MS;
  return { provider, model, timeoutMs };
}

interface ParsedArgs {
  provider: Provider;
  model: string;
  question: string;
}

function parseArgs(raw: string, fallbackProvider: Provider, fallbackModel: string): ParsedArgs {
  const parts = raw.trim().split(/\s+/).filter(Boolean);
  let provider = fallbackProvider;
  let model = fallbackModel;
  const rest: string[] = [];

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];
    if (part === "--claude") {
      provider = "claude";
    } else if (part === "--codex") {
      provider = "codex";
    } else if (part === "--fable") {
      // Shorthand: Fable 5 runs through the Claude backend with a model override.
      provider = "claude";
      model = FABLE_MODEL;
    } else if (part === "--model") {
      provider = "claude";
      model = parts[++i] ?? "";
    } else {
      rest.push(part);
    }
  }

  // A model override only applies to the Claude backend; Codex ignores it.
  if (provider === "codex") model = "";
  return { provider, model, question: rest.join(" ").trim() };
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

async function runClaude(
  pi: ExtensionAPI,
  ctx: ExtensionContext,
  prompt: string,
  timeoutMs: number,
  model: string,
) {
  // Fable 5 is pricier, so give it a little more budget headroom than the
  // default Claude model while still capping the spend.
  const budget = model === FABLE_MODEL ? "1.50" : "0.50";
  const args = [
    "-p",
    "--no-session-persistence",
    "--permission-mode",
    "plan",
    "--tools",
    "",
    "--max-budget-usd",
    budget,
    ...(model ? ["--model", model] : []),
    prompt,
  ];
  return pi.exec("claude", args, { cwd: ctx.cwd, timeout: timeoutMs });
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
    description: "Read-only second opinion: /consult [--claude|--codex|--fable|--model <id>] <question>",
    handler: async (args, ctx) => {
      const settings = getSettings(ctx);
      const { provider, model, question } = parseArgs(args, settings.provider, settings.model);

      if (!question) {
        ctx.ui.notify(
          "Usage: /consult [--claude|--codex|--fable|--model <id>] <question>\n" +
            "Example: /consult --fable adversarially review this design for blind spots",
          "warning",
        );
        return;
      }

      const label = provider === "claude" && model ? `claude (${model})` : provider;
      ctx.ui.notify(`Consulting ${label}…`, "info");
      const prompt = consultPrompt(question, ctx.cwd);
      const result = provider === "claude"
        ? await runClaude(pi, ctx, prompt, settings.timeoutMs, model)
        : await runCodex(pi, ctx, prompt, settings.timeoutMs);

      if (result.code !== 0) {
        const details = truncate(result.stderr || result.stdout || "No output");
        ctx.ui.notify(`Consult failed (${label})\n${details}`, "warning");
        return;
      }

      ctx.ui.notify(`Consultation (${label})\n\n${truncate(result.stdout)}`, "info");
    },
  });
}
