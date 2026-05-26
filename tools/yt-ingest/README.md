# yt-ingest

Pipeline for ingesting a Netscape-format YouTube bookmarks export into an Obsidian-style learning queue. Cross-verifies every Gemini-generated summary against YouTube oEmbed metadata to catch hallucinations, retries transient failures, and aggregates persistent failures into a markdown checklist for browser review.

Built and battle-tested during a 105-video catch-up batch in May 2026 (47/105 needed manual review -- mostly shorts Gemini can't access, plus a handful of clear hallucinations the verifier caught).

## Why

Gemini's YouTube understanding is unreliable in measurable ways:

- For some videos (especially shorts, recent uploads, restricted content), the tool returns wholly fabricated summaries with no disclosure.
- For others, the tool fails silently with empty output.
- For most well-known videos, it works fine.

`yt-ingest` separates these cases by always cross-checking Gemini's returned title against the authoritative oEmbed title for the same URL. Mismatches get flagged, not written as if true.

## Install

```bash
uv tool install ~/dotfiles/tools/yt-ingest
```

Or run directly from source:

```bash
cd ~/dotfiles/tools/yt-ingest
uv run yt-ingest --help
```

## Commands

```
yt-ingest parse <bookmarks.html> <out.tsv>
    Extract YouTube URLs (with folder + title context) from a Netscape bookmarks HTML.

yt-ingest triage <in.tsv> --keep keep.tsv --skip skip.tsv
    Classify into keepers vs skips (gaming, memes, trailers, off-topic news).

yt-ingest process <keep.tsv> <results.tsv> --start N --end M --parallelism K
    Run Gemini + oEmbed for a row range. Appends to results TSV.

yt-ingest retry <results.tsv> <failures.md>
    Retry every unverified row once. Recovered rows get their TSV row updated;
    persistent failures appended to the markdown checklist.

yt-ingest write <results.tsv> <queue-dir> [--force]
    Generate Watch-*.md queue items in the target dir.

yt-ingest run <bookmarks.html> --queue-dir DIR --failures FILE [--batch-size 20]
    Full pipeline: parse -> triage -> process (in batches) -> retry -> write.
```

## Pipeline Detail

For each URL:

1. **oEmbed lookup** -- canonical title + channel from YouTube's official endpoint. This is the ground truth.
2. **Gemini summary call** -- `gemini -p "..."` with a prompt that includes an explicit `CANNOT ACCESS VIDEO` escape hatch so Gemini can disclose failure instead of fabricating.
3. **Fuzzy title match** -- compares Gemini's reported `TITLE:` against oEmbed's. Loose match (3+ shared meaningful words) counts as verified.
4. **Mismatch handling** -- title divergence usually indicates Gemini hallucinated a wholly different video; the queue item is written with the oEmbed-verified metadata only and a "summary unavailable" notice, and the URL is logged to the failures markdown.
5. **Retry** -- a single retry pass before declaring failure.

## Output Format

Each queue item is a markdown file with frontmatter:

```yaml
---
tags: [learn]
domain: [...lazy tags...]
priority: 1 | 2 | 3 | 4        # 1=now · 2=next · 3=later · 4=someday
status: queue
added: YYYY-MM-DD
source: <canonical URL>
source_title: "<oembed title>"
source_channel: "<oembed channel>"
source_duration: "..."
verified: true | false
verification_note: "..."
impact: [...]
---

# Watch -- [Title](URL)

**Channel:** ... | **Duration:** ...

## Summary (Gemini, verified) | Summary (unavailable) | Summary (title mismatch -- verify)

...

## Why this is queued

Bookmarked under `<folder>`. Worth evaluating; haven't watched yet.

## Notes (during consumption)
## Verbalize
## Recall Cards
```

The failures markdown is a checklist:

```markdown
- [ ] [Title](URL) -- channel: `...` -- **reason**: ... -- *added YYYY-MM-DD*
```

## Caveats

- `parallelism` over ~10 tends to hit Gemini rate limits; default is 10.
- The script doesn't actually watch videos -- it asks Gemini to. If Gemini's coverage gets better, this whole tool gets better for free.
- Domain-tag inference is heuristic (string matching on title + folder + tools). Tune in `writer.py:domain_tags()` for your taxonomy.

## License

Personal infrastructure. Not licensed for redistribution -- but the patterns are general; lift what's useful.
