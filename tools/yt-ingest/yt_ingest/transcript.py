"""Transcript-mode pipeline: fetch YouTube auto-captions via yt-dlp, summarize via a text model.

Sidesteps Gemini Pro's quota (it's needed for native video understanding) and the
hallucination problem (model reads the actual transcript text rather than pretending
to watch).
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .pipeline import (
    GEMINI_NOISE_PREFIXES,
    GEMINI_NOISE_SUBSTRINGS,
    canonicalize_url,
    oembed,
    parse_gemini,
)

# Default model for text summarization. Flash Lite has separate quota from Pro
# and is reliable for text tasks (just not native video understanding).
DEFAULT_TRANSCRIPT_MODEL = "gemini-2.5-flash-lite"

# Hard cap on transcript size sent to the model. Flash Lite has a huge context
# window, but very long transcripts waste tokens. ~200k chars ≈ ~50k tokens.
MAX_TRANSCRIPT_CHARS = 200_000

TRANSCRIPT_PROMPT_TEMPLATE = """\
You are summarizing a YouTube video using its auto-generated transcript. Be factual; do not invent content not present in the transcript.

Video title (authoritative -- copy verbatim): {title}
Channel: {channel}
URL: {url}

Transcript:
{transcript}

Return EXACTLY this format (no preamble, no commentary):

TITLE: {title}
CHANNEL: {channel}
DURATION: <approximate runtime if inferable from transcript timestamps, else 'unknown'>
SUMMARY: <3-4 sentences, factual, based only on what is in the transcript above>
KEY THESIS: <one-sentence main argument the speaker makes, or 'unclear' if transcript is ambiguous>
EPISTEMIC NOTES: <one sentence: is this consensus knowledge, a survey of views, or one speaker's opinionated thesis? Note if speaker cites sources.>
TOOLS/CONCEPTS MENTIONED: <comma-separated list of specific tools/libraries/frameworks/technical concepts named in the transcript, or 'none'>

If the transcript is empty, unreadable, or doesn't contain meaningful spoken content, return only the TITLE / CHANNEL lines plus:
SUMMARY: Transcript empty or no meaningful content.
"""


# ---------- yt-dlp transcript fetching ----------


def _strip_vtt(vtt_text: str) -> str:
    """Convert WebVTT to plain text. Drop timestamps, cue settings, and HTML tags."""
    lines = []
    seen_lines = set()  # Auto-captions often repeat each line
    for raw in vtt_text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        # Skip WEBVTT header, cue identifiers, timestamps
        if line.startswith("WEBVTT"):
            continue
        if "-->" in line:
            continue
        if re.fullmatch(r"\d+", line):  # cue number
            continue
        if (
            line.startswith("Kind:")
            or line.startswith("Language:")
            or line.startswith("NOTE")
        ):
            continue
        # Strip HTML/timing tags from caption text
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if not line or line in seen_lines:
            continue
        seen_lines.add(line)
        lines.append(line)
    return "\n".join(lines)


def fetch_transcript(url: str, timeout: int = 60) -> dict:
    """Fetch English auto-captions for a YouTube URL. Returns {'ok', 'text', 'error'}."""
    canon = canonicalize_url(url)
    with tempfile.TemporaryDirectory(prefix="yt-ingest-") as tmp:
        tmpdir = Path(tmp)
        # yt-dlp args: subs only, skip download, english, vtt output, quiet
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-auto-sub",
            "--sub-lang",
            "en,en-US,en-GB,en-orig",
            "--sub-format",
            "vtt",
            "--convert-subs",
            "vtt",
            "--no-warnings",
            "--quiet",
            "-o",
            str(tmpdir / "%(id)s"),
            canon,
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "text": "", "error": "yt-dlp timeout"}
        except FileNotFoundError:
            return {"ok": False, "text": "", "error": "yt-dlp not installed"}
        except Exception as e:
            return {"ok": False, "text": "", "error": f"yt-dlp error: {e}"}

        if result.returncode != 0:
            return {
                "ok": False,
                "text": "",
                "error": f"yt-dlp rc={result.returncode}: {result.stderr.strip()[:200]}",
            }

        vtts = list(tmpdir.glob("*.vtt"))
        if not vtts:
            return {"ok": False, "text": "", "error": "no captions available"}

        # Prefer non-auto-translated; pick first found
        # Auto-generated files have ".en.vtt" or similar; manual has same. Take whichever exists.
        text = _strip_vtt(vtts[0].read_text(encoding="utf-8", errors="replace"))
        if not text.strip():
            return {"ok": False, "text": "", "error": "transcript empty after parse"}
        return {"ok": True, "text": text[:MAX_TRANSCRIPT_CHARS], "error": ""}


# ---------- Gemini call (text-only, Flash Lite default) ----------


def summarize_transcript(
    transcript: str,
    title: str,
    channel: str,
    url: str,
    model: str = DEFAULT_TRANSCRIPT_MODEL,
    timeout: int = 120,
) -> dict:
    """Call Gemini (default Flash Lite) to summarize a transcript. Returns parsed dict."""
    prompt = TRANSCRIPT_PROMPT_TEMPLATE.format(
        title=title, channel=channel, url=url, transcript=transcript
    )
    try:
        result = subprocess.run(
            ["gemini", "-m", model, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "gemini timeout"}
    except Exception as e:
        return {"ok": False, "error": f"gemini error: {e}"}

    lines = result.stdout.split("\n")
    filtered = [
        ln
        for ln in lines
        if not any(ln.startswith(p) for p in GEMINI_NOISE_PREFIXES)
        and not any(s in ln for s in GEMINI_NOISE_SUBSTRINGS)
    ]
    raw = "\n".join(filtered).strip()
    if not raw:
        return {"ok": False, "error": "gemini returned empty output"}
    return {"ok": True, "raw": raw, "parsed": parse_gemini(raw)}


# ---------- Per-row orchestration ----------


def process_transcript_one(
    folder: str,
    bookmark_title: str,
    url: str,
    model: str = DEFAULT_TRANSCRIPT_MODEL,
) -> dict:
    """Full transcript-mode pipeline for one URL. Matches process_one's output schema."""
    oem = oembed(url)
    transcript_result = fetch_transcript(url)

    canon = canonicalize_url(url)

    if not transcript_result["ok"]:
        return _make_row(
            folder,
            bookmark_title,
            url,
            canon,
            oem,
            verified=False,
            note=f"transcript: {transcript_result['error']}",
        )

    summ = summarize_transcript(
        transcript_result["text"], oem["title"], oem["channel"], canon, model=model
    )
    if not summ["ok"]:
        return _make_row(
            folder,
            bookmark_title,
            url,
            canon,
            oem,
            verified=False,
            note=f"summarize: {summ['error']}",
        )

    parsed = summ["parsed"]
    summary_text = parsed.get("SUMMARY", "")
    # Transcript-mode verification: the model read actual content, so summary
    # length is the proxy for "real summary vs refusal".
    if (
        len(summary_text) > 60
        and "transcript empty" not in summary_text.lower()
        and "no meaningful content" not in summary_text.lower()
    ):
        verified = True
        note = f"verified via transcript ({len(transcript_result['text'])} chars)"
    else:
        verified = False
        note = "transcript summary too short or empty"

    return _make_row(
        folder,
        bookmark_title,
        url,
        canon,
        oem,
        verified=verified,
        note=note,
        parsed=parsed,
    )


def _make_row(
    folder: str,
    bookmark_title: str,
    url: str,
    canon: str,
    oem: dict,
    verified: bool,
    note: str,
    parsed: dict | None = None,
) -> dict:
    parsed = parsed or {}
    return {
        "folder": folder,
        "bookmark_title": bookmark_title,
        "url": url,
        "canon_url": canon,
        "oembed_title": oem["title"],
        "oembed_channel": oem["channel"],
        "gemini_title": parsed.get("TITLE", oem["title"]),
        "gemini_channel": parsed.get("CHANNEL", oem["channel"]),
        "gemini_duration": parsed.get("DURATION", ""),
        "gemini_summary": parsed.get("SUMMARY", ""),
        "gemini_thesis": parsed.get("KEY THESIS", ""),
        "gemini_epistemic": parsed.get("EPISTEMIC NOTES", ""),
        "gemini_tools": parsed.get("TOOLS/CONCEPTS MENTIONED", ""),
        "verified": verified,
        "note": note,
    }


# ---------- Batch ----------


def process_transcript_batch(
    rows: list[tuple[str, str, str]],
    parallelism: int = 5,
    model: str = DEFAULT_TRANSCRIPT_MODEL,
) -> list[dict]:
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=parallelism) as ex:
        futures = {ex.submit(process_transcript_one, *r, model): r for r in rows}
        for fut in as_completed(futures):
            results.append(fut.result())
    order = {row[2]: i for i, row in enumerate(rows)}
    results.sort(key=lambda r: order.get(r["url"], 9999))
    return results
