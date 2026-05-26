"""Triage URLs into keepers vs skips by pattern matching on title and URL."""

from __future__ import annotations

import re
from pathlib import Path

# (regex pattern, skip reason) -- ordered; first match wins.
DEFAULT_SKIP_PATTERNS: list[tuple[str, str]] = [
    (r"project zomboid|world records|indie game.*standup", "gaming/entertainment"),
    (
        r"enraged.*embarrassed|paragliding.*dodo|skincare|hair loss drug|chronic issues|"
        r"stuck with your genes|harvard mindset.*shorts|guitar|comping.*double stops|"
        r"i quit my tech job|told you so|i got \d+ world records",
        "entertainment/meme short",
    ),
    (
        r"netflix.*trailer|official trailer|theroux.*manosphere|everyone is lying to you for money",
        "trailer/marketing",
    ),
    (
        r"trump|billionaire oligarchs|war with iran|ukraine.*drones|stocks rallied|revolutions are led",
        "off-topic politics/news",
    ),
    (r"darkest manga|50 cent", "entertainment"),
    (r"/results\?", "search URL not a video"),
    (r"^'$", "malformed title"),
    (r"#guitar|#skincare|#shorts|#dermatologist|#wait", "personal-care/health short"),
    (
        r"openai is broke|brace yourself for the ai bubble",
        "clickbait opinion short",
    ),
]


def classify(
    rows: list[dict], skip_patterns: list[tuple[str, str]] | None = None
) -> tuple[list[dict], list[dict]]:
    """Return (keepers, skips). Skips have an extra `reason` field."""
    patterns = skip_patterns or DEFAULT_SKIP_PATTERNS
    keep: list[dict] = []
    skip: list[dict] = []
    for r in rows:
        haystack = f"{r['title'].lower()} {r['url'].lower()}"
        reason: str | None = None
        for pat, why in patterns:
            if re.search(pat, haystack, re.IGNORECASE):
                reason = why
                break
        # Per-title manual overrides for things regex can't easily catch:
        if r["title"].strip() == "'":
            reason = "malformed title"
        if "/results?" in r["url"]:
            reason = "search URL not a video"
        if reason:
            skip.append({**r, "reason": reason})
        else:
            keep.append(r)
    return keep, skip


def write_keep_skip_tsvs(
    keep: list[dict], skip: list[dict], keep_path: Path, skip_path: Path
) -> None:
    keep_path.parent.mkdir(parents=True, exist_ok=True)
    skip_path.parent.mkdir(parents=True, exist_ok=True)

    def _esc(s: str) -> str:
        return s.replace("\t", " ").replace("\n", " ")

    with keep_path.open("w") as f:
        f.write("folder\ttitle\turl\n")
        for r in keep:
            f.write(f"{_esc(r['folder'])}\t{_esc(r['title'])}\t{r['url']}\n")
    with skip_path.open("w") as f:
        f.write("folder\ttitle\turl\treason\n")
        for r in skip:
            f.write(
                f"{_esc(r['folder'])}\t{_esc(r['title'])}\t{r['url']}\t{r['reason']}\n"
            )
