"""Gemini + oEmbed pipeline with cross-verification and retry."""

from __future__ import annotations

import json
import re
import subprocess
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

RESULT_HEADERS = [
    "folder",
    "bookmark_title",
    "url",
    "canon_url",
    "oembed_title",
    "oembed_channel",
    "gemini_title",
    "gemini_channel",
    "gemini_duration",
    "gemini_summary",
    "gemini_thesis",
    "gemini_epistemic",
    "gemini_tools",
    "verified",
    "note",
]

GEMINI_PROMPT_TEMPLATE = (
    "Watch this YouTube video and return a tight structured summary: {url}\n\n"
    "Return EXACTLY this format (no preamble):\n\n"
    "TITLE: <video title>\n"
    "CHANNEL: <channel name>\n"
    "DURATION: <approximate runtime>\n"
    "SUMMARY: <3-4 sentences, factual about content>\n"
    "KEY THESIS: <one-sentence main argument>\n"
    "EPISTEMIC NOTES: <consensus / survey / opinionated thesis? Cite sources speaker uses>\n"
    "TOOLS/CONCEPTS MENTIONED: <comma-separated list, or 'none'>\n"
    "\nIf you cannot actually access this specific video, say so explicitly with "
    "'CANNOT ACCESS VIDEO' as the first line."
)

# Gemini CLI prints these as boilerplate; filter them out of the response.
GEMINI_NOISE_PREFIXES = ("Ripgrep", "Skill ", "Attempt ")
GEMINI_NOISE_SUBSTRINGS = ("LocalAgentExecutor",)


# ---------- URL canonicalization ----------


def canonicalize_url(url: str) -> str:
    m = re.search(r"(?:v=|/shorts/)([A-Za-z0-9_-]{11})", url)
    if m:
        return f"https://www.youtube.com/watch?v={m.group(1)}"
    m = re.search(r"list=([A-Za-z0-9_-]+)", url)
    if m:
        return f"https://youtube.com/playlist?list={m.group(1)}"
    return url


# ---------- oEmbed ----------


def oembed(url: str) -> dict:
    canon = canonicalize_url(url)
    endpoint = f"https://www.youtube.com/oembed?url={urllib.parse.quote(canon, safe='')}&format=json"
    try:
        req = urllib.request.Request(endpoint, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            return {
                "title": data.get("title", ""),
                "channel": data.get("author_name", ""),
                "ok": True,
            }
    except Exception as e:
        return {"title": "", "channel": "", "ok": False, "error": str(e)}


# ---------- Gemini ----------


def gemini_call(url: str, timeout: int = 180) -> dict:
    canon = canonicalize_url(url)
    prompt = GEMINI_PROMPT_TEMPLATE.format(url=canon)
    try:
        result = subprocess.run(
            ["gemini", "-p", prompt], capture_output=True, text=True, timeout=timeout
        )
        lines = result.stdout.split("\n")
        filtered = [
            ln
            for ln in lines
            if not any(ln.startswith(p) for p in GEMINI_NOISE_PREFIXES)
            and not any(s in ln for s in GEMINI_NOISE_SUBSTRINGS)
        ]
        return {"ok": True, "raw": "\n".join(filtered).strip()}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def parse_gemini(raw: str) -> dict:
    out: dict = {}
    for line in raw.split("\n"):
        m = re.match(
            r"^(TITLE|CHANNEL|DURATION|SUMMARY|KEY THESIS|EPISTEMIC NOTES|TOOLS/CONCEPTS MENTIONED|CANNOT ACCESS VIDEO):\s*(.*)$",
            line.strip(),
        )
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    if "CANNOT ACCESS VIDEO" in raw:
        out["__cannot_access__"] = True
    return out


# ---------- Title matching ----------

_STOPWORDS = {
    "the",
    "a",
    "an",
    "is",
    "in",
    "of",
    "for",
    "to",
    "and",
    "or",
    "youtube",
    "with",
    "you",
    "your",
    "how",
    "what",
    "why",
    "be",
    "on",
    "i",
    "it",
    "this",
    "that",
}


def _normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def titles_match(t1: str, t2: str) -> bool:
    if not t1 or not t2:
        return False
    w1 = set(_normalize(t1).split()) - _STOPWORDS
    w2 = set(_normalize(t2).split()) - _STOPWORDS
    overlap = w1 & w2
    return len(overlap) >= 3 or (len(w1) <= 4 and len(overlap) >= 2)


# ---------- Single-row processing ----------


def process_one(folder: str, bookmark_title: str, url: str) -> dict:
    """Run oEmbed + Gemini + comparison for a single URL."""
    oem = oembed(url)
    gem = gemini_call(url)
    parsed = parse_gemini(gem.get("raw", "")) if gem["ok"] else {}

    verified = False
    if not gem["ok"]:
        note = f"gemini error: {gem.get('error', 'unknown')}"
    elif parsed.get("__cannot_access__"):
        note = "gemini said cannot access"
    elif not oem["ok"]:
        note = "oembed failed; cannot verify"
    elif titles_match(oem["title"], parsed.get("TITLE", "")):
        verified = True
        note = "verified"
    else:
        note = (
            f"title mismatch: oembed={oem['title'][:50]!r} "
            f"gemini={parsed.get('TITLE', '')[:50]!r}"
        )

    return {
        "folder": folder,
        "bookmark_title": bookmark_title,
        "url": url,
        "canon_url": canonicalize_url(url),
        "oembed_title": oem["title"],
        "oembed_channel": oem["channel"],
        "gemini_title": parsed.get("TITLE", ""),
        "gemini_channel": parsed.get("CHANNEL", ""),
        "gemini_duration": parsed.get("DURATION", ""),
        "gemini_summary": parsed.get("SUMMARY", ""),
        "gemini_thesis": parsed.get("KEY THESIS", ""),
        "gemini_epistemic": parsed.get("EPISTEMIC NOTES", ""),
        "gemini_tools": parsed.get("TOOLS/CONCEPTS MENTIONED", ""),
        "verified": verified,
        "note": note,
    }


# ---------- Batch processing ----------


def process_batch(
    rows: list[tuple[str, str, str]], parallelism: int = 10
) -> list[dict]:
    """Run process_one in parallel for a batch of (folder, title, url) tuples."""
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=parallelism) as ex:
        futures = {ex.submit(process_one, *r): r for r in rows}
        for fut in as_completed(futures):
            results.append(fut.result())
    # Preserve input order
    order = {row[2]: i for i, row in enumerate(rows)}
    results.sort(key=lambda r: order.get(r["url"], 9999))
    return results


# ---------- TSV I/O ----------


def append_results(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not out_path.exists() or out_path.stat().st_size == 0
    with out_path.open("a") as f:
        if write_header:
            f.write("\t".join(RESULT_HEADERS) + "\n")
        for r in rows:
            row = [
                str(r.get(h, "")).replace("\t", " ").replace("\n", " ")
                for h in RESULT_HEADERS
            ]
            f.write("\t".join(row) + "\n")


def read_results(path: Path) -> list[dict]:
    lines = path.read_text().strip().split("\n")
    headers = lines[0].split("\t")
    return [dict(zip(headers, line.split("\t"))) for line in lines[1:]]


def write_results(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        f.write("\t".join(RESULT_HEADERS) + "\n")
        for r in rows:
            row = [
                str(r.get(h, "")).replace("\t", " ").replace("\n", " ")
                for h in RESULT_HEADERS
            ]
            f.write("\t".join(row) + "\n")


# ---------- Retry ----------


def _retry_one(row: dict) -> tuple[dict, bool]:
    if "cannot access" in row["note"]:
        # Gemini explicitly disclosed; retry won't help.
        return row, False
    raw = gemini_call(row["url"])
    if not raw["ok"]:
        row["note"] = f"gemini error on retry: {raw.get('error')}"
        row["verified"] = "False"
        return row, False
    parsed = parse_gemini(raw["raw"])
    if parsed.get("__cannot_access__"):
        row["note"] = "gemini said cannot access (on retry)"
        row["verified"] = "False"
        return row, False
    new_title = parsed.get("TITLE", "")
    if titles_match(row["oembed_title"], new_title):
        row.update(
            {
                "gemini_title": new_title,
                "gemini_channel": parsed.get("CHANNEL", ""),
                "gemini_duration": parsed.get("DURATION", ""),
                "gemini_summary": parsed.get("SUMMARY", ""),
                "gemini_thesis": parsed.get("KEY THESIS", ""),
                "gemini_epistemic": parsed.get("EPISTEMIC NOTES", ""),
                "gemini_tools": parsed.get("TOOLS/CONCEPTS MENTIONED", ""),
                "verified": "True",
                "note": "verified on retry",
            }
        )
        return row, True
    row["gemini_title"] = new_title
    row["note"] = (
        f"title mismatch on retry: oembed={row['oembed_title'][:40]!r} gemini={new_title[:40]!r}"
    )
    row["verified"] = "False"
    return row, False


def retry_failures(
    rows: list[dict], parallelism: int = 8
) -> tuple[list[dict], list[dict]]:
    """Retry all unverified rows once. Returns (recovered, still_failed)."""
    failures = [r for r in rows if r["verified"] != "True"]
    recovered: list[dict] = []
    still_failed: list[dict] = []
    with ThreadPoolExecutor(max_workers=parallelism) as ex:
        futures = {ex.submit(_retry_one, dict(r)): r for r in failures}
        for fut in as_completed(futures):
            new_row, ok = fut.result()
            (recovered if ok else still_failed).append(new_row)
    return recovered, still_failed


# ---------- Failure markdown ----------

FAILURE_HEADER = """\
---
tags: [bookmarks, failures, youtube]
---

# YouTube Summary Failures

Videos where Gemini could not produce a verified summary even after one retry. Watch in browser to capture content -- or remove the corresponding queue item if not worth your time.

Failure categories:
- **Gemini cannot access this video** -- Gemini's YouTube tool returns nothing; usually for shorts, very recent uploads, or restricted content
- **Title mismatch** -- Gemini returned a summary for a different video at that URL; likely hallucination
- **gemini error** -- network/quota/timeout

## Items

"""


def append_failures(rows: list[dict], failures_md: Path) -> int:
    """Append still-failed rows to the failures markdown. Returns count of new entries."""
    failures_md.parent.mkdir(parents=True, exist_ok=True)
    existing_urls: set[str] = set()
    if failures_md.exists():
        for m in re.finditer(r"\((https?://[^)]+)\)", failures_md.read_text()):
            existing_urls.add(canonicalize_url(m.group(1)))
    else:
        failures_md.write_text(FAILURE_HEADER)

    today = date.today().isoformat()
    new_lines: list[str] = []
    for r in rows:
        canon = r["canon_url"]
        if canon in existing_urls:
            continue
        existing_urls.add(canon)
        if "cannot access" in r["note"]:
            reason = "Gemini cannot access this video"
        elif "mismatch" in r["note"]:
            reason = "Title mismatch with oEmbed (likely hallucination)"
        else:
            reason = r["note"]
        title = r["oembed_title"] or r["bookmark_title"]
        channel = r["oembed_channel"]
        new_lines.append(
            f"- [ ] [{title}]({canon}) -- channel: `{channel}` -- **reason**: {reason} -- *added {today}*"
        )

    if new_lines:
        with failures_md.open("a") as f:
            for line in new_lines:
                f.write(line + "\n")
    return len(new_lines)
