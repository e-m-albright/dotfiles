import type { AssistantMessage } from "@mariozechner/pi-ai";
import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";

type GitState =
	| { kind: "not-git" }
	| {
			kind: "git";
			branch: string;
			worktreeName?: string;
			staged: number;
			unstaged: number;
			untracked: number;
			conflicts: number;
			ahead: number;
			behind: number;
		};

type QuotaState =
	| { kind: "unknown" }
	| { kind: "percent"; usedPercent: number; source: string };

function formatTokens(count: number): string {
	if (count < 1000) return count.toString();
	if (count < 10000) return `${(count / 1000).toFixed(1)}k`;
	if (count < 1000000) return `${Math.round(count / 1000)}k`;
	if (count < 10000000) return `${(count / 1000000).toFixed(1)}M`;
	return `${Math.round(count / 1000000)}M`;
}

const ANSI_RESET = "\x1b[0m";
const ANSI_DIM = "\x1b[2m";

function color(hex: string, text: string): string {
	if (process.env.NO_COLOR) return text;
	const normalized = hex.replace(/^#/, "");
	const r = Number.parseInt(normalized.slice(0, 2), 16);
	const g = Number.parseInt(normalized.slice(2, 4), 16);
	const b = Number.parseInt(normalized.slice(4, 6), 16);
	return `\x1b[38;2;${r};${g};${b}m${text}${ANSI_RESET}`;
}

function dim(text: string): string {
	return process.env.NO_COLOR ? text : `${ANSI_DIM}${text}${ANSI_RESET}`;
}

function amberRamp(percent: number | null | undefined, text: string): string {
	if (percent === null || percent === undefined) return dim(text);
	if (percent >= 90) return color("#d9784d", text); // burnt amber, not alarm red
	if (percent >= 75) return color("#d9913d", text); // orange amber
	if (percent >= 55) return color("#d3b15f", text); // distinct gold
	return color("#8fa879", text); // muted sage
}

function statusColor(kind: "good" | "note" | "warn" | "danger", text: string): string {
	switch (kind) {
		case "good":
			return color("#8fa879", text);
		case "note":
			return color("#80a6ad", text);
		case "warn":
			return color("#d9913d", text);
		case "danger":
			return color("#d9784d", text);
	}
}

async function git(pi: ExtensionAPI, cwd: string, args: string[]) {
	return pi.exec("git", ["--no-optional-locks", ...args], { cwd, timeout: 1000 });
}

function countPorcelain(lines: string[]) {
	let staged = 0;
	let unstaged = 0;
	let untracked = 0;
	let conflicts = 0;

	for (const line of lines) {
		const status = line.slice(0, 2);
		const index = status[0];
		const worktree = status[1];

		if (status === "??") {
			untracked++;
			continue;
		}

		if (["DD", "AU", "UD", "UA", "DU", "AA", "UU"].includes(status)) {
			conflicts++;
			continue;
		}

		if (index && index !== " " && index !== "?") staged++;
		if (worktree && worktree !== " " && worktree !== "?") unstaged++;
	}

	return { staged, unstaged, untracked, conflicts };
}

async function getGitState(pi: ExtensionAPI, cwd: string): Promise<GitState> {
	const inside = await git(pi, cwd, ["rev-parse", "--is-inside-work-tree"]);
	if (inside.code !== 0 || inside.stdout.trim() !== "true") return { kind: "not-git" };

	const [branchResult, statusResult, gitDirResult, commonDirResult, topLevelResult, aheadBehindResult] =
		await Promise.all([
			git(pi, cwd, ["symbolic-ref", "--quiet", "--short", "HEAD"]),
			git(pi, cwd, ["status", "--porcelain"]),
			git(pi, cwd, ["rev-parse", "--path-format=absolute", "--git-dir"]),
			git(pi, cwd, ["rev-parse", "--path-format=absolute", "--git-common-dir"]),
			git(pi, cwd, ["rev-parse", "--show-toplevel"]),
			git(pi, cwd, ["rev-list", "--left-right", "--count", "HEAD...@{u}"]),
		]);

	let branch = branchResult.stdout.trim();
	if (!branch) {
		const detached = await git(pi, cwd, ["rev-parse", "--short", "HEAD"]);
		branch = detached.stdout.trim() || "detached";
	}

	const lines = statusResult.stdout.trim().split("\n").filter(Boolean);
	const counts = countPorcelain(lines);

	const gitDir = gitDirResult.stdout.trim();
	const commonDir = commonDirResult.stdout.trim();
	const topLevel = topLevelResult.stdout.trim();
	let worktreeName: string | undefined;
	if (gitDir && commonDir && gitDir !== commonDir && topLevel) {
		worktreeName = topLevel.split("/").filter(Boolean).pop();
	}

	let ahead = 0;
	let behind = 0;
	if (aheadBehindResult.code === 0) {
		const [aheadText, behindText] = aheadBehindResult.stdout.trim().split(/\s+/);
		ahead = Number.parseInt(aheadText ?? "0", 10) || 0;
		behind = Number.parseInt(behindText ?? "0", 10) || 0;
	}

	return { kind: "git", branch, worktreeName, ...counts, ahead, behind };
}

function gitSegment(state: GitState): string {
	if (state.kind !== "git") return "";

	const parts: string[] = [state.branch];
	if (state.worktreeName) parts.push(statusColor("note", `wt:${state.worktreeName}`));

	if (state.conflicts > 0) parts.push(statusColor("danger", `!${state.conflicts}`));
	if (state.staged > 0) parts.push(statusColor("warn", `+${state.staged}`));
	if (state.unstaged > 0) parts.push(statusColor("warn", `*${state.unstaged}`));
	if (state.untracked > 0) parts.push(statusColor("warn", `?${state.untracked}`));
	if (state.ahead > 0) parts.push(statusColor("note", `⇡${state.ahead}`));
	if (state.behind > 0) parts.push(statusColor("warn", `⇣${state.behind}`));

	if (parts.length === 1) {
		parts.push(statusColor("good", "✓"));
	}

	return `${dim("(")}${parts.join(" ")}${dim(")")}`;
}

function authClass(ctx: ExtensionContext): "local" | "subscription" | "paid" {
	const model = ctx.model;
	if (!model) return "paid";
	const isZeroCost =
		model.cost.input === 0 &&
		model.cost.output === 0 &&
		model.cost.cacheRead === 0 &&
		model.cost.cacheWrite === 0;
	if (model.provider.includes("lm-studio") || model.provider.includes("ollama") || isZeroCost) return "local";
	if (ctx.modelRegistry.isUsingOAuth(model)) return "subscription";
	return "paid";
}

function authSegment(ctx: ExtensionContext, totalCost: number, quotaState: QuotaState): string {
	switch (authClass(ctx)) {
		case "local":
			return statusColor("good", "local");
		case "subscription":
			if (quotaState.kind === "percent") {
				return amberRamp(quotaState.usedPercent, `sub ${Math.round(quotaState.usedPercent)}%`);
			}
			return statusColor("note", "sub");
		case "paid":
			return statusColor("danger", `api $${totalCost.toFixed(3)}`);
	}
}

function modelSegment(ctx: ExtensionContext): string {
	const model = ctx.model;
	if (!model) return dim("no-model");
	const label = `${model.provider}/${model.id}`;
	switch (authClass(ctx)) {
		case "local":
			return statusColor("good", label);
		case "subscription":
			return statusColor("note", label);
		case "paid":
			return statusColor("danger", label);
	}
}

function parsePositiveNumber(value: string | undefined): number | undefined {
	if (!value) return undefined;
	const parsed = Number.parseFloat(value);
	return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}

function quotaFromHeaders(headers: Record<string, string>): QuotaState {
	const get = (name: string) => headers[name.toLowerCase()] ?? headers[name];
	const candidates: Array<[string, string, string]> = [
		["x-ratelimit-limit-tokens", "x-ratelimit-remaining-tokens", "tokens"],
		["x-ratelimit-limit-requests", "x-ratelimit-remaining-requests", "requests"],
		["openai-processing-ms-limit", "openai-processing-ms-remaining", "processing"],
	];

	for (const [limitHeader, remainingHeader, source] of candidates) {
		const limit = parsePositiveNumber(get(limitHeader));
		const remaining = parsePositiveNumber(get(remainingHeader));
		if (!limit || remaining === undefined) continue;
		const usedPercent = Math.max(0, Math.min(100, ((limit - remaining) / limit) * 100));
		return { kind: "percent", usedPercent, source };
	}

	return { kind: "unknown" };
}

function renderFooter(ctx: ExtensionContext, gitState: GitState, quotaState: QuotaState, width: number): string[] {
	const theme = ctx.ui.theme;
	const entries = ctx.sessionManager.getEntries();
	let totalInput = 0;
	let totalOutput = 0;
	let totalCacheRead = 0;
	let totalCacheWrite = 0;
	let totalCost = 0;

	for (const entry of entries) {
		if (entry.type !== "message" || entry.message.role !== "assistant") continue;
		const message = entry.message as AssistantMessage;
		totalInput += message.usage.input;
		totalOutput += message.usage.output;
		totalCacheRead += message.usage.cacheRead;
		totalCacheWrite += message.usage.cacheWrite;
		totalCost += message.usage.cost.total;
	}

	const home = process.env.HOME || process.env.USERPROFILE || "";
	let cwd = ctx.cwd;
	if (home && cwd.startsWith(home)) cwd = `~${cwd.slice(home.length)}`;

	const gitText = gitSegment(gitState);
	const sessionName = ctx.sessionManager.getSessionName();
	let pathLine = gitText ? `${dim(cwd)} ${gitText}` : dim(cwd);
	if (sessionName) pathLine += dim(` • ${sessionName}`);
	const coloredPathLine = truncateToWidth(pathLine, width, dim("..."));

	const usage = ctx.getContextUsage();
	const contextWindow = usage?.contextWindow ?? ctx.model?.contextWindow ?? 0;
	const contextPercentValue = usage?.percent ?? 0;
	const contextPercent = usage?.percent === null || usage?.percent === undefined ? "?" : usage.percent.toFixed(1);
	const contextTokens = usage?.tokens === null || usage?.tokens === undefined ? "?" : formatTokens(usage.tokens);
	const groupSep = dim("   ");
	const tokenParts: string[] = [];
	if (totalInput) tokenParts.push(dim(` ${formatTokens(totalInput)}`));
	if (totalOutput) tokenParts.push(dim(` ${formatTokens(totalOutput)}`));
	const cacheParts: string[] = [];
	if (totalCacheRead) cacheParts.push(dim(` ${formatTokens(totalCacheRead)}`));
	if (totalCacheWrite) cacheParts.push(dim(` ${formatTokens(totalCacheWrite)}`));

	const groups = [
		amberRamp(contextPercentValue, `ctx: ${contextPercent}% ${contextTokens}/${formatTokens(contextWindow)}`),
		authSegment(ctx, totalCost, quotaState),
	];
	if (tokenParts.length > 0) groups.push(`${dim("io:")} ${tokenParts.join(dim(" "))}`);
	if (cacheParts.length > 0) groups.push(`${dim("cache-io:")} ${cacheParts.join(dim(" "))}`);

	let left = groups.join(groupSep);
	let leftWidth = visibleWidth(left);
	if (leftWidth > width) {
		left = truncateToWidth(left, width, "...");
		leftWidth = visibleWidth(left);
	}

	const right = modelSegment(ctx);
	const rightWidth = visibleWidth(right);
	let statsLine: string;
	if (leftWidth + 2 + rightWidth <= width) {
		statsLine = left + " ".repeat(width - leftWidth - rightWidth) + right;
	} else {
		const availableRight = width - leftWidth - 2;
		if (availableRight > 0) {
			const truncatedRight = truncateToWidth(right, availableRight, "");
			statsLine = left + " ".repeat(Math.max(1, width - leftWidth - visibleWidth(truncatedRight))) + truncatedRight;
		} else {
			statsLine = left;
		}
	}

	return [coloredPathLine, truncateToWidth(statsLine, width, dim("..."))];
}

export default function (pi: ExtensionAPI) {
	let gitState: GitState = { kind: "not-git" };
	let quotaState: QuotaState = { kind: "unknown" };
	let refreshTimer: ReturnType<typeof setInterval> | undefined;
	let refreshInFlight = false;
	let requestRender: (() => void) | undefined;

	const refresh = async (ctx: ExtensionContext) => {
		if (refreshInFlight) return;
		refreshInFlight = true;
		try {
			gitState = await getGitState(pi, ctx.cwd);
			requestRender?.();
		} finally {
			refreshInFlight = false;
		}
	};

	pi.on("session_start", async (_event, ctx) => {
		if (!ctx.hasUI) return;
		ctx.ui.setStatus("git-dirty", undefined);
		await refresh(ctx);

		ctx.ui.setFooter((tui) => {
			requestRender = () => tui.requestRender();
			return {
				dispose() {
					requestRender = undefined;
				},
				invalidate() {},
				render(width: number): string[] {
					return renderFooter(ctx, gitState, quotaState, width);
				},
			};
		});

		refreshTimer && clearInterval(refreshTimer);
		refreshTimer = setInterval(() => {
			void refresh(ctx);
		}, 3000);
	});

	pi.on("tool_execution_end", async (_event, ctx) => {
		await refresh(ctx);
	});

	pi.on("user_bash", async (_event, ctx) => {
		await refresh(ctx);
	});

	pi.on("after_provider_response", async (event, ctx) => {
		if (ctx.model?.provider !== "openai-codex") return;
		quotaState = quotaFromHeaders(event.headers as Record<string, string>);
		requestRender?.();
	});

	pi.on("session_shutdown", async () => {
		if (refreshTimer) {
			clearInterval(refreshTimer);
			refreshTimer = undefined;
		}
		requestRender = undefined;
	});
}
