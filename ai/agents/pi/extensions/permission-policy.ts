import { existsSync, readFileSync } from "node:fs";
import { join, normalize, resolve } from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { getAgentDir } from "@earendil-works/pi-coding-agent";

interface DenyCommandRule {
  name: string;
  patterns: string[];
}

interface PermissionPolicy {
  defaultAction?: "allow" | "deny";
  denyCommands?: DenyCommandRule[];
  protectedPaths?: string[];
}

const FALLBACK_POLICY: Required<PermissionPolicy> = {
  defaultAction: "allow",
  denyCommands: [],
  protectedPaths: [
    ".env",
    ".env.*",
    "**/.env",
    "**/.env.*",
    "**/secrets/**",
    "**/*key*",
    "**/*token*",
    "**/*credential*",
    "~/.ssh/**",
    "~/.aws/**",
    "~/.config/gh/**",
    ".git/**",
    "node_modules/**",
  ],
};

function readPolicyFile(path: string): PermissionPolicy {
  if (!existsSync(path)) return {};
  try {
    return JSON.parse(readFileSync(path, "utf8")) as PermissionPolicy;
  } catch (error) {
    throw new Error(`Invalid permission policy at ${path}: ${error}`);
  }
}

function loadPolicy(cwd: string): Required<PermissionPolicy> {
  const globalPolicy = readPolicyFile(join(getAgentDir(), "permission-policy.json"));
  const projectPolicy = readPolicyFile(join(cwd, ".pi", "permission-policy.json"));

  return {
    defaultAction: projectPolicy.defaultAction ?? globalPolicy.defaultAction ?? FALLBACK_POLICY.defaultAction,
    denyCommands: [
      ...FALLBACK_POLICY.denyCommands,
      ...(globalPolicy.denyCommands ?? []),
      ...(projectPolicy.denyCommands ?? []),
    ],
    protectedPaths: [
      ...FALLBACK_POLICY.protectedPaths,
      ...(globalPolicy.protectedPaths ?? []),
      ...(projectPolicy.protectedPaths ?? []),
    ],
  };
}

function globToRegExp(glob: string): RegExp {
  let pattern = glob.replace(/^~(?=\/|$)/, process.env.HOME ?? "~");
  pattern = normalize(pattern);

  const escaped = pattern
    .replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    .replace(/\\\*\\\*/g, ".*")
    .replace(/\\\*/g, "[^/]*");

  return new RegExp(`(^|/)${escaped}($|/)`, "i");
}

function normalizeCandidatePath(cwd: string, candidate: string): string {
  const withoutQuotes = candidate.replace(/^['\"]|['\"]$/g, "");
  if (withoutQuotes.startsWith("~")) return normalize(withoutQuotes.replace(/^~/, process.env.HOME ?? "~"));
  if (withoutQuotes.startsWith("/")) return normalize(withoutQuotes);
  return normalize(resolve(cwd, withoutQuotes));
}

function pathMatchesPolicy(cwd: string, path: string, protectedPathGlobs: string[]): string | undefined {
  const normalized = normalizeCandidatePath(cwd, path);
  const relative = normalize(path.replace(/^\.\//, ""));

  for (const glob of protectedPathGlobs) {
    const regex = globToRegExp(glob);
    if (regex.test(normalized) || regex.test(relative)) return glob;
  }

  return undefined;
}

function extractInputPaths(input: unknown): string[] {
  if (!input || typeof input !== "object") return [];
  const record = input as Record<string, unknown>;
  const paths = new Set<string>();

  for (const key of ["path", "file", "target", "source"] as const) {
    const value = record[key];
    if (typeof value === "string") paths.add(value);
  }

  const multi = record.multi;
  if (Array.isArray(multi)) {
    for (const item of multi) {
      if (!item || typeof item !== "object") continue;
      const itemPath = (item as Record<string, unknown>).path;
      if (typeof itemPath === "string") paths.add(itemPath);
    }
  }

  return [...paths];
}

function protectedPathMention(cwd: string, command: string, protectedPathGlobs: string[]): string | undefined {
  const tokens = command.match(/(?:[^\s"']+|"[^"]*"|'[^']*')+/g) ?? [];
  for (const token of tokens) {
    const cleaned = token.replace(/^['\"]|['\"]$/g, "");
    const looksLikePath = cleaned.includes("/") || cleaned.startsWith(".") || cleaned.startsWith("~");
    if (!looksLikePath) continue;

    const matched = pathMatchesPolicy(cwd, cleaned, protectedPathGlobs);
    if (matched) return matched;
  }
  return undefined;
}

function commandDenyReason(command: string, rules: DenyCommandRule[]): string | undefined {
  for (const rule of rules) {
    for (const pattern of rule.patterns) {
      if (new RegExp(pattern, "i").test(command)) return rule.name;
    }
  }
  return undefined;
}

function block(reason: string) {
  return { block: true, reason };
}

export default function permissionPolicyExtension(pi: ExtensionAPI) {
  let lastPolicy: Required<PermissionPolicy> | undefined;

  function policyFor(ctx: ExtensionContext) {
    lastPolicy = loadPolicy(ctx.cwd);
    return lastPolicy;
  }

  pi.registerCommand("permissions-status", {
    description: "Show active Pi permission policy summary",
    handler: async (_args, ctx) => {
      const policy = policyFor(ctx);
      ctx.ui.notify(
        [
          "Permission policy",
          `  Default action: ${policy.defaultAction}`,
          `  Deny command groups: ${policy.denyCommands.length}`,
          `  Protected path globs: ${policy.protectedPaths.length}`,
          "  Source: ~/.pi/agent/permission-policy.json plus optional .pi/permission-policy.json",
        ].join("\n"),
        "info",
      );
    },
  });

  pi.on("tool_call", async (event, ctx) => {
    const policy = policyFor(ctx);

    if (["read", "write", "edit"].includes(event.toolName)) {
      for (const candidate of extractInputPaths(event.input)) {
        const matched = pathMatchesPolicy(ctx.cwd, candidate, policy.protectedPaths);
        if (matched) return block(`Protected path blocked by policy: ${matched}`);
      }
    }

    if (event.toolName !== "bash") return undefined;

    const command = String((event.input as Record<string, unknown>).command ?? "");
    const protectedPath = protectedPathMention(ctx.cwd, command, policy.protectedPaths);
    if (protectedPath) return block(`Command mentions protected path: ${protectedPath}`);

    const denied = commandDenyReason(command, policy.denyCommands);
    if (denied) return block(`Command blocked by policy: ${denied}`);

    if (policy.defaultAction === "deny") return block("Command blocked by default-deny policy");
    return undefined;
  });
}
