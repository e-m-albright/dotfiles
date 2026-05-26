#!/usr/bin/env python3
"""scripts/check_baselines.py — validates code-health baselines.

Reads baselines.json at repo root. For each metric:
  counts.<key>             grep-count an anti-pattern; must be <= ceiling
  file_ceilings.<path>     line count of file; must be <= ceiling

Exit 0 if all pass, 1 if any fail.

Modes:
  (default)         enforce ceilings, exit non-zero on regression
  --auto-ratchet    rewrite baselines.json to current (lower) values

Project owns the metric definitions in METRICS below. Add/remove freely.
The shape (pattern + paths + glob) lets the same script work across stacks.

No external deps; uses ripgrep if present, falls back to grep.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(
    subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
)
BASELINES_PATH = REPO_ROOT / "baselines.json"

# Project-owned metric definitions. Each entry maps a baselines.counts.<key>
# to a search recipe. Add metrics for the suppressions/anti-patterns you care
# about; remove ones that don't apply to your stack.
METRICS: dict[str, dict] = {
    "todo_total": {
        "pattern": r"(TODO|FIXME|XXX)",
        "paths": ["src/", "lib/", "app/"],
        "globs": ["*.py", "*.ts", "*.tsx", "*.svelte", "*.rs", "*.go"],
        "description": "TODO/FIXME/XXX in source",
    },
    "type_ignore_total": {
        "pattern": r"# type: ignore|@ts-ignore|@ts-expect-error",
        "paths": ["src/", "lib/", "app/"],
        "globs": ["*.py", "*.ts", "*.tsx", "*.svelte"],
        "description": "type-system suppressions",
    },
    "as_any_total": {
        "pattern": r"\bas any\b|\bas unknown\b",
        "paths": ["src/", "lib/", "app/"],
        "globs": ["*.ts", "*.tsx", "*.svelte"],
        "description": "TS 'as any' / 'as unknown' upcasts",
    },
}

EXCLUDE_DIRS = {
    "target",
    "node_modules",
    ".venv",
    ".svelte-kit",
    "dist",
    "build",
    "__pycache__",
    ".next",
    ".turbo",
    ".worktrees",
    ".git",
}


def grep_count(pattern: str, paths: list[str], globs: list[str]) -> int:
    """Count matches across paths. Uses ripgrep if available, falls back to grep."""
    existing_paths = [str(REPO_ROOT / p) for p in paths if (REPO_ROOT / p).exists()]
    if not existing_paths:
        return 0

    if shutil.which("rg"):
        cmd = ["rg", "--count-matches", "--no-heading", pattern]
        for g in globs:
            cmd += ["-g", g]
        for d in EXCLUDE_DIRS:
            cmd += ["-g", f"!{d}"]
        cmd += existing_paths
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode not in (0, 1):
            print(f"  WARNING: rg failed: {result.stderr.strip()}", file=sys.stderr)
            return 0
        total = 0
        for line in result.stdout.strip().splitlines():
            _, _, n = line.rpartition(":")
            try:
                total += int(n)
            except ValueError:
                continue
        return total

    # grep fallback
    cmd = ["grep", "-rE", pattern]
    for g in globs:
        cmd += ["--include", g]
    for d in EXCLUDE_DIRS:
        cmd += [f"--exclude-dir={d}"]
    cmd += existing_paths
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        print(f"  WARNING: grep failed: {result.stderr.strip()}", file=sys.stderr)
        return 0
    return len(result.stdout.strip().splitlines()) if result.stdout.strip() else 0


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open() as f:
        return sum(1 for _ in f)


def load_baselines() -> dict:
    return json.loads(BASELINES_PATH.read_text())


def save_baselines(data: dict) -> None:
    BASELINES_PATH.write_text(json.dumps(data, indent="\t") + "\n")


def check(auto_ratchet: bool = False) -> int:
    if not BASELINES_PATH.exists():
        print(
            f"FAIL: {BASELINES_PATH.relative_to(REPO_ROOT)} not found", file=sys.stderr
        )
        return 1

    baselines = load_baselines()
    counts = {
        k: v for k, v in baselines.get("counts", {}).items() if not k.startswith("_")
    }
    file_ceilings = {
        k: v
        for k, v in baselines.get("file_ceilings", {}).items()
        if not k.startswith("_")
    }

    failures = 0
    improvements: dict[str, int] = {}

    print("Counts:")
    for key, ceiling in counts.items():
        spec = METRICS.get(key)
        if not spec:
            print(f"  ?  {key}: ceiling={ceiling} but no METRICS entry — skipping")
            continue
        actual = grep_count(spec["pattern"], spec["paths"], spec["globs"])
        if actual > ceiling:
            print(f"  ✗  {key}: {actual} > {ceiling}  ({spec['description']})")
            failures += 1
        elif actual < ceiling:
            print(
                f"  ↓  {key}: {actual} < {ceiling}  (improvement; ratchet to {actual})"
            )
            improvements[f"counts.{key}"] = actual
        else:
            print(f"  ✓  {key}: {actual}")

    print("\nFile ceilings:")
    for path_str, ceiling in file_ceilings.items():
        actual = count_lines(REPO_ROOT / path_str)
        if actual > ceiling:
            print(f"  ✗  {path_str}: {actual} > {ceiling}")
            failures += 1
        elif actual < ceiling:
            print(f"  ↓  {path_str}: {actual} < {ceiling}  (ratchet to {actual})")
            improvements[f"file_ceilings.{path_str}"] = actual
        else:
            print(f"  ✓  {path_str}: {actual}")

    if auto_ratchet and improvements:
        for key, new_val in improvements.items():
            section, _, name = key.partition(".")
            baselines[section][name] = new_val
        save_baselines(baselines)
        print(f"\nAuto-ratcheted {len(improvements)} metric(s) → baselines.json")
        return 0

    if failures:
        print(f"\nFAIL: {failures} ceiling(s) exceeded.", file=sys.stderr)
        print(
            "Fix the regression or, if unavoidable, raise the ceiling with justification.",
            file=sys.stderr,
        )
        return 1

    if improvements and not auto_ratchet:
        print(
            f"\n{len(improvements)} ceiling(s) could be tightened. Run with --auto-ratchet to apply."
        )

    print("\nOK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate code-health baselines")
    parser.add_argument(
        "--auto-ratchet",
        action="store_true",
        help="Lower ceilings to match current (improved) values",
    )
    args = parser.parse_args()
    return check(auto_ratchet=args.auto_ratchet)


if __name__ == "__main__":
    sys.exit(main())
