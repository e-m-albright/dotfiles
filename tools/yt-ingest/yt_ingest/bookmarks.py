"""Parse Netscape-format bookmarks HTML, extracting YouTube URLs with folder + title context."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path


class _BookmarksParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.folder_stack: list[str] = []
        self.in_h3 = False
        self.in_a = False
        self.pending_h3 = ""
        self.pending_a_href: str | None = None
        self.pending_a_title = ""
        self.results: list[dict] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_d = dict(attrs)
        if tag == "h3":
            self.in_h3 = True
            self.pending_h3 = ""
        elif tag == "a":
            self.in_a = True
            self.pending_a_href = attrs_d.get("href", "")
            self.pending_a_title = ""
        elif tag == "dl" and self.pending_h3:
            self.folder_stack.append(self.pending_h3)
            self.pending_h3 = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "h3":
            self.in_h3 = False
        elif tag == "a":
            self.in_a = False
            href = self.pending_a_href or ""
            title = (self.pending_a_title or "").strip()
            if "youtube.com" in href or "youtu.be" in href:
                self.results.append(
                    {
                        "title": title,
                        "url": href,
                        "folder": " / ".join(self.folder_stack),
                    }
                )
            self.pending_a_href = None
            self.pending_a_title = ""
        elif tag == "dl" and self.folder_stack:
            self.folder_stack.pop()

    def handle_data(self, data: str) -> None:
        if self.in_h3:
            self.pending_h3 += data
        elif self.in_a:
            self.pending_a_title += data


def extract_youtube_urls(html_path: Path) -> list[dict]:
    """Return deduped list of {folder, title, url} dicts for every YouTube link in the bookmarks file.

    Dedupe key: canonical video ID (or playlist ID, or full URL fallback).
    """
    html = html_path.read_text(encoding="utf-8", errors="replace")
    parser = _BookmarksParser()
    parser.feed(html)

    seen: dict[str, dict] = {}
    for entry in parser.results:
        url = entry["url"]
        m = re.search(r"v=([A-Za-z0-9_-]{11})", url)
        if m:
            key = f"v={m.group(1)}"
        else:
            m = re.search(r"list=([A-Za-z0-9_-]+)", url)
            key = f"list={m.group(1)}" if m else url
        seen.setdefault(key, entry)
    return list(seen.values())


def write_tsv(rows: list[dict], out_path: Path) -> None:
    """Write rows as TSV with columns: folder, title, url."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        f.write("folder\ttitle\turl\n")
        for r in rows:
            folder = r["folder"].replace("\t", " ").replace("\n", " ")
            title = r["title"].replace("\t", " ").replace("\n", " ")
            f.write(f"{folder}\t{title}\t{r['url']}\n")
