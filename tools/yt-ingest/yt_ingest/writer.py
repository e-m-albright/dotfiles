"""Generate Learn/Professional/ queue items from a results TSV."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .pipeline import read_results


# ---------- Filename slug ----------


def slugify(s: str, max_len: int = 80) -> str:
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"-+", "-", s)
    return s[:max_len]


# ---------- Dedup: scan queue dir for existing video IDs ----------


def existing_video_ids(queue_dir: Path) -> set[str]:
    ids: set[str] = set()
    if not queue_dir.exists():
        return ids
    for f in queue_dir.glob("*.md"):
        content = f.read_text()
        for m in re.finditer(r"(?:v=|/shorts/)([A-Za-z0-9_-]{11})", content):
            ids.add(m.group(1))
        for m in re.finditer(r"list=([A-Za-z0-9_-]+)", content):
            ids.add(m.group(1))
    return ids


# ---------- Tag inference ----------


def domain_tags(
    folder: str, oembed_title: str, gemini_tools: str, bookmark_title: str
) -> list[str]:
    text = f"{folder} {oembed_title} {gemini_tools} {bookmark_title}".lower()
    tags: set[str] = set()
    if any(
        k in text
        for k in [
            "claude code",
            "cursor",
            "codex",
            "claude",
            "copilot",
            "ai coding",
            "spec-driven",
        ]
    ):
        tags.add("ai-engineering")
    if any(k in text for k in ["agent", "harness", "mcp", "skill"]):
        tags.add("agent-harnesses")
    if any(k in text for k in ["obsidian", "knowledge graph", "second brain"]):
        tags.add("knowledge-management")
    if any(
        k in text
        for k in ["rust", "python", "c++", "ffmpeg", "data-intensive", "kleppmann"]
    ):
        tags.add("programming")
    if any(
        k in text for k in ["bubble", "openai financial", "circular financing", "stock"]
    ):
        tags.add("business-strategy")
    if any(
        k in text
        for k in [
            "brain",
            "mindset",
            "cognitive",
            "procrastinate",
            "shame",
            "psychedelic",
        ]
    ):
        tags.add("personal-growth")
    if not tags:
        tags.add("ai-engineering")
    return sorted(tags)


# ---------- Priority heuristic ----------


def priority_default(folder: str, title: str, canon_url: str) -> int:
    # Numeric priority: 1=now · 2=next · 3=later · 4=someday
    if "/shorts/" in canon_url:
        return 4
    text = (folder + " " + title).lower()
    if any(
        k in text
        for k in [
            "claude code best practices",
            "spec-driven",
            "kleppmann",
            "designing data-intensive",
            "karpathy",
            "anthropic",
        ]
    ):
        return 2
    return 3


# ---------- Summary block ----------


def _summary_block(row: dict) -> str:
    verified = row["verified"] == "True"
    note = row["note"]
    if verified:
        return (
            f"## Summary (Gemini, verified)\n\n"
            f"{row['gemini_summary']}\n\n"
            f"**Key thesis (per speaker):** {row['gemini_thesis']}\n\n"
            f"**Epistemic note:** {row['gemini_epistemic']}\n\n"
            f"**Tools/concepts mentioned:** {row['gemini_tools']}\n"
        )
    if "cannot access" in note:
        return (
            "## Summary\n\n"
            "*Summary unavailable -- Gemini could not access this specific video. "
            "Watch in browser to capture content.*\n"
        )
    if "gemini error" in note:
        return (
            "## Summary\n\n"
            "*Summary unavailable -- Gemini call errored. Retry or watch in browser.*\n"
        )
    if "title mismatch" in note or "mismatch" in note:
        return (
            f"## Summary (Gemini, **title mismatch -- verify before trusting**)\n\n"
            f"> Gemini returned title `{row['gemini_title'][:100]}` which does not match the "
            f"oEmbed-verified title above. The summary below may be for a different video. "
            f"Treat as unverified until watched.\n\n"
            f"{row['gemini_summary']}\n\n"
            f"**Reported key thesis:** {row['gemini_thesis']}\n\n"
            f"**Reported epistemic note:** {row['gemini_epistemic']}\n\n"
            f"**Reported tools/concepts:** {row['gemini_tools']}\n"
        )
    return f"## Summary\n\n*Status: {note}*\n"


# ---------- Render one queue item ----------


def render_item(
    row: dict, queue_dir: Path, existing_ids: set[str], force: bool = False
) -> tuple[str | None, str]:
    canon = row["canon_url"]
    vid_match = re.search(r"v=([A-Za-z0-9_-]{11})", canon) or re.search(
        r"list=([A-Za-z0-9_-]+)", canon
    )
    vid = vid_match.group(1) if vid_match else ""
    if vid in existing_ids and not force:
        return None, f"skip dupe: {vid}"

    oembed_title = row["oembed_title"] or row["bookmark_title"]
    channel = row["oembed_channel"] or "unknown"
    slug = slugify(oembed_title) or vid or "untitled"
    filename = f"Watch-{slug}.md"
    path = queue_dir / filename
    if path.exists() and not force:
        return None, f"skip existing file: {filename}"

    verified = row["verified"] == "True"
    duration = row["gemini_duration"]
    domain = domain_tags(
        row["folder"], oembed_title, row["gemini_tools"], row["bookmark_title"]
    )
    priority = priority_default(row["folder"], oembed_title, canon)

    body = f"""---
tags: [learn]
domain: {domain}
priority: {priority}
status: queue
added: {date.today().isoformat()}
last_reviewed: null
source: {canon}
source_title: "{oembed_title}"
source_channel: "{channel}"
source_duration: "{duration}"
verified: {str(verified).lower()}
verification_note: "{row["note"]}"
impact: [code]
---

# Watch -- [{oembed_title}]({canon})

**Channel:** {channel}{f" | **Duration:** {duration}" if duration else ""}

{_summary_block(row)}

## Why this is queued

Bookmarked under `{row["folder"] or "uncategorized"}`. Worth evaluating; haven't watched yet.

## Notes (during consumption)

<!-- Capture during watch. Especially: what the speaker actually argues vs the title's pitch; whether the takeaway holds up; tools/practices worth adopting. -->

## Verbalize (own words, 3-5 sentences)

## Recall Cards
"""
    queue_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return filename, "written"


def write_all(
    results_tsv: Path, queue_dir: Path, force: bool = False
) -> tuple[list[str], list[tuple[str, str]]]:
    rows = read_results(results_tsv)
    existing = existing_video_ids(queue_dir)
    written: list[str] = []
    skipped: list[tuple[str, str]] = []
    for r in rows:
        fn, status = render_item(r, queue_dir, existing, force=force)
        if fn:
            written.append(fn)
        else:
            skipped.append((r["oembed_title"] or r["bookmark_title"], status))
    return written, skipped
