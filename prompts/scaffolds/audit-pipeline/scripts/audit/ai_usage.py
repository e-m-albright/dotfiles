#!/usr/bin/env python3
"""scripts/audit/ai_usage.py — produces raw.json for the ai-usage audit.

Checks the project's `.ai/` tree and AGENTS.md for:
  1. token-budget       Line/char/token estimates for AGENTS.md and rules
                        with `alwaysApply: true`.
  2. frontmatter        Validate YAML frontmatter across rules, skills,
                        and prompts.
  3. dead-links         Verify markdown links resolve (relative file paths only;
                        HTTP checks skipped unless AI_AUDIT_HTTP=1).

Emits raw.json with the same schema as scripts/audit/security.sh:
  {
    "topic": "ai-usage",
    "ts": "...",
    "started_at": "...",
    "completed_at": "...",
    "run_dir": "...",
    "tools": [
      {"name": "...", "status": "...", "output_file": "...",
       "error": "...", "duration_ms": N, "install_cmd": ""}
    ]
  }

Usage:  scripts/audit/ai_usage.py [run-dir]
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(
    subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
)
AI_DIR = REPO_ROOT / ".ai"

CHARS_PER_TOKEN = 4
LINK_RE = re.compile(r"\[(?P<text>[^\]]*)\]\((?P<url>[^)\s]+)(?:\s+\"[^\"]*\")?\)")
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")


def now_ms() -> int:
    return int(time.time() * 1000)


def read_text(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def parse_frontmatter(text: str) -> tuple[dict[str, str] | None, str | None]:
    """Return (parsed_dict, error). Best-effort YAML — no PyYAML dependency.

    Only handles flat key:value pairs (sufficient for our frontmatter).
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, "missing frontmatter"
    body = m.group(1)
    out: dict[str, str] = {}
    for raw in body.splitlines():
        line = raw.rstrip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            return None, f"malformed line (no ':'): {line!r}"
        key, _, val = line.partition(":")
        out[key.strip()] = val.strip().strip("\"'")
    return out, None


def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


# --- Check 1: token-budget --------------------------------------------------


def check_token_budget(run_dir: Path) -> dict:
    """Estimate token cost of always-on context."""
    start = now_ms()
    entries: list[dict] = []
    total_tokens = 0

    candidates = [
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "CLAUDE.md",
        REPO_ROOT / "GEMINI.md",
    ]
    for p in candidates:
        if p.exists() and not p.is_symlink():
            text = read_text(p) or ""
            tok = estimate_tokens(text)
            total_tokens += tok
            entries.append(
                {
                    "path": str(p.relative_to(REPO_ROOT)),
                    "tokens": tok,
                    "lines": text.count("\n"),
                }
            )

    rules_dir = AI_DIR / "rules"
    if rules_dir.exists():
        for mdc in sorted(rules_dir.rglob("*.mdc")):
            text = read_text(mdc) or ""
            fm, _ = parse_frontmatter(text)
            if fm and fm.get("alwaysApply", "").lower() == "true":
                tok = estimate_tokens(text)
                total_tokens += tok
                entries.append(
                    {
                        "path": str(mdc.relative_to(REPO_ROOT)),
                        "tokens": tok,
                        "lines": text.count("\n"),
                    }
                )

    out = run_dir / "token-budget.json"
    out.write_text(
        json.dumps({"total_tokens": total_tokens, "entries": entries}, indent=2)
    )

    status = "ok" if total_tokens < 20000 else "findings"
    return {
        "name": "token-budget",
        "status": status,
        "output_file": "token-budget.json",
        "error": ""
        if status == "ok"
        else f"always-on context exceeds 20k tokens ({total_tokens})",
        "duration_ms": now_ms() - start,
        "install_cmd": "",
    }


# --- Check 2: frontmatter ---------------------------------------------------


def check_frontmatter(run_dir: Path) -> dict:
    start = now_ms()
    issues: list[dict] = []

    targets: list[Path] = []
    for sub in ("rules", "prompts", "skills"):
        d = AI_DIR / sub
        if d.exists():
            targets.extend(d.rglob("*.md"))
            targets.extend(d.rglob("*.mdc"))

    for p in sorted(set(targets)):
        text = read_text(p)
        if text is None:
            issues.append(
                {"path": str(p.relative_to(REPO_ROOT)), "error": "could not read"}
            )
            continue
        if p.name == "README.md":
            continue
        fm, err = parse_frontmatter(text)
        if err:
            issues.append({"path": str(p.relative_to(REPO_ROOT)), "error": err})
        elif fm and "name" not in fm and "description" not in fm:
            issues.append(
                {
                    "path": str(p.relative_to(REPO_ROOT)),
                    "error": "frontmatter missing both 'name' and 'description'",
                }
            )

    out = run_dir / "frontmatter.json"
    out.write_text(json.dumps({"issues": issues}, indent=2))
    status = "ok" if not issues else "findings"
    return {
        "name": "frontmatter",
        "status": status,
        "output_file": "frontmatter.json",
        "error": ""
        if status == "ok"
        else f"{len(issues)} files with frontmatter issues",
        "duration_ms": now_ms() - start,
        "install_cmd": "",
    }


# --- Check 3: dead-links ----------------------------------------------------


def check_dead_links(run_dir: Path) -> dict:
    start = now_ms()
    dead: list[dict] = []
    check_http = os.environ.get("AI_AUDIT_HTTP") == "1"
    skipped_http = 0

    targets: list[Path] = []
    for sub in ("rules", "prompts", "skills"):
        d = AI_DIR / sub
        if d.exists():
            targets.extend(d.rglob("*.md"))
            targets.extend(d.rglob("*.mdc"))
    if (REPO_ROOT / "AGENTS.md").exists():
        targets.append(REPO_ROOT / "AGENTS.md")

    for p in sorted(set(targets)):
        text = read_text(p) or ""
        for m in LINK_RE.finditer(text):
            url = m.group("url").strip()
            if url.startswith(("http://", "https://")):
                if not check_http:
                    skipped_http += 1
                continue
            if url.startswith("#"):
                continue
            target = (p.parent / url.split("#", 1)[0]).resolve()
            if not target.exists():
                dead.append(
                    {
                        "source": str(p.relative_to(REPO_ROOT)),
                        "link": url,
                        "resolved_to": str(target),
                    }
                )

    out = run_dir / "dead-links.json"
    out.write_text(
        json.dumps({"dead_links": dead, "http_skipped": skipped_http}, indent=2)
    )
    status = "ok" if not dead else "findings"
    return {
        "name": "dead-links",
        "status": status,
        "output_file": "dead-links.json",
        "error": "" if status == "ok" else f"{len(dead)} dead relative links",
        "duration_ms": now_ms() - start,
        "install_cmd": "",
    }


# --- main -------------------------------------------------------------------


def main() -> int:
    started_at = now_iso()
    ts = now_ts()
    if len(sys.argv) > 1:
        run_dir = Path(sys.argv[1])
    else:
        run_dir = REPO_ROOT / ".ai" / "artifacts" / "audits" / "ai-usage" / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"Running ai-usage checks → {run_dir.relative_to(REPO_ROOT)}", file=sys.stderr
    )

    tools = [
        check_token_budget(run_dir),
        check_frontmatter(run_dir),
        check_dead_links(run_dir),
    ]

    raw = {
        "topic": "ai-usage",
        "ts": ts,
        "started_at": started_at,
        "completed_at": now_iso(),
        "run_dir": str(run_dir),
        "tools": tools,
    }
    (run_dir / "raw.json").write_text(json.dumps(raw, indent=2))

    print("", file=sys.stderr)
    for t in tools:
        marker = {"ok": "✓", "findings": "⚠", "error": "✗", "not-installed": "○"}.get(
            t["status"], "?"
        )
        msg = f"  {marker} {t['name']}: {t['status']}"
        if t["error"]:
            msg += f" — {t['error']}"
        print(msg, file=sys.stderr)
    print(f"\nWrote: {run_dir.relative_to(REPO_ROOT)}/raw.json", file=sys.stderr)

    has_findings = any(t["status"] == "findings" for t in tools)
    return 1 if has_findings else 0


if __name__ == "__main__":
    sys.exit(main())
