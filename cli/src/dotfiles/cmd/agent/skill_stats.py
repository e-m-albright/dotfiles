"""agent stats — skill-usage analytics mined from agent transcripts.

A trigger-quality instrument, not a usage counter. It reads Claude Code session
transcripts (``~/.claude/projects/**/*.jsonl``), extracts every ``Skill``
invocation, classifies each as **explicit** (you typed ``/skill``) or
**autonomous** (the model chose it from the skill's ``description:``), and
cross-references the canonical ``ai/skills/`` inventory to surface:

- **dead skills** — deployed but never fired in the window (prune candidates);
- **weak triggers** — only ever reached by typing the slash command, i.e. the
  ``description:`` isn't earning autonomous invocations;
- recurring **sequences** (skills that chain).

Readers are ports: ``ClaudeTranscriptReader`` and ``CodexTranscriptReader`` emit
the same ``SkillEvent`` stream behind one service. Cursor is GUI-only and leaves
no parseable logs, so it is honestly uncovered.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Protocol, cast

# A user-typed slash command surfaces in the transcript as
# ``<command-name>/skill-name</command-name>``. Built-in commands (/compact,
# /login) match too but simply never align with a skill name, so they're inert.
_CMD_RE = re.compile(r"<command-name>\s*/?([A-Za-z0-9:_-]+)")

_SPARK = "▁▂▃▄▅▆▇█"
_BUCKETS = 8


# ---------------------------------------------------------------------------
# Normalized event — the seam every vendor reader emits
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillEvent:
    """One skill invocation, normalized across vendors."""

    skill: str
    vendor: str
    project: str
    timestamp: datetime
    explicit: bool
    session_id: str


def _short(skill: str) -> str:
    """Last segment of a namespaced skill name: ``superpowers:x`` -> ``x``."""
    return skill.split(":")[-1]


# ---------------------------------------------------------------------------
# Defensive JSON accessors (transcript schema is undocumented and shifts)
# ---------------------------------------------------------------------------


def _as_dict(value: object) -> dict[str, object] | None:
    return cast("dict[str, object]", value) if isinstance(value, dict) else None


def _as_list(value: object) -> list[object] | None:
    return cast("list[object]", value) if isinstance(value, list) else None


def _as_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _skill_uses(obj: dict[str, object]) -> list[str]:
    """Skill names from an assistant message's ``tool_use`` blocks."""
    message = _as_dict(obj.get("message"))
    content = _as_list(message.get("content")) if message else None
    if content is None:
        return []
    out: list[str] = []
    for raw_block in content:
        block = _as_dict(raw_block)
        if block is None or block.get("type") != "tool_use" or block.get("name") != "Skill":
            continue
        inp = _as_dict(block.get("input"))
        skill = _as_str(inp.get("skill")) if inp else None
        if skill:
            out.append(skill)
    return out


def _command_skill(raw: str) -> str | None:
    """Skill name from a ``<command-name>/skill</command-name>`` user message."""
    match = _CMD_RE.search(raw)
    return match.group(1) if match else None


def _timestamp(obj: dict[str, object]) -> datetime | None:
    raw = _as_str(obj.get("timestamp"))
    if raw is None:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _project(obj: dict[str, object], path: Path) -> str:
    cwd = _as_str(obj.get("cwd"))
    return Path(cwd).name if cwd else path.parent.name


# ---------------------------------------------------------------------------
# Reader ports — each vendor emits the same SkillEvent stream
# ---------------------------------------------------------------------------


class TranscriptReader(Protocol):
    """A per-vendor source of normalized skill invocations."""

    dropped_lines: int

    def events(self) -> Iterator[SkillEvent]: ...


class ClaudeTranscriptReader:
    """Stream ``SkillEvent``s from ``~/.claude/projects/**/*.jsonl``."""

    vendor = "claude"

    def __init__(self, home: Path) -> None:
        self._root = home / ".claude" / "projects"
        self.dropped_lines = 0

    def events(self) -> Iterator[SkillEvent]:
        if not self._root.is_dir():
            return
        for jsonl in sorted(self._root.glob("*/*.jsonl")):
            yield from self._read_file(jsonl)

    def _read_file(self, path: Path) -> Iterator[SkillEvent]:
        for raw in _iter_lines(path):
            obj = _decode(raw)
            if obj is None:
                self.dropped_lines += 1
                continue
            yield from _line_events(raw, obj, path, self.vendor)


def _line_events(raw: str, obj: dict[str, object], path: Path, vendor: str) -> Iterator[SkillEvent]:
    """Skill events from one transcript line.

    Two invocation sources, NOT the same event double-counted: a user-typed slash
    command is EXPLICIT and surfaces as ``<command-name>`` (the harness loads it
    directly, never via a Skill tool_use); a Skill tool_use the model chose from a
    ``description:`` is AUTONOMOUS. Built-in slashes (/compact, /login) are emitted
    too and filtered by the service.
    """
    timestamp = _timestamp(obj)
    if timestamp is None:
        return
    session = _as_str(obj.get("sessionId")) or path.stem
    project = _project(obj, path)
    kind = obj.get("type")
    if kind == "user":
        slash = _command_skill(raw)
        if slash is not None:
            yield SkillEvent(slash, vendor, project, timestamp, True, session)
    elif kind == "assistant":
        for skill in _skill_uses(obj):
            yield SkillEvent(skill, vendor, project, timestamp, False, session)


# A Codex skill open is an exec_command whose cmd reads `…/skills/<name>/SKILL.md`.
# The direct `skills/<name>/SKILL.md` shape excludes Codex's own `.system/*`
# builtins, whose extra path segment breaks the match.
_SKILL_PATH = re.compile(r"(?:^|/)skills/([a-z0-9][a-z0-9-]*)/SKILL\.md")


class CodexTranscriptReader:
    """Stream ``SkillEvent``s from Codex rollouts in ``~/.codex/{,archived_}sessions``.

    Codex has no Skill tool: the model loads a skill by reading its ``SKILL.md``
    after picking it from the described catalog, so an open is one AUTONOMOUS
    (description-driven) use. Slash-invoked opens aren't separable, so Codex never
    contributes EXPLICIT events. De-duplicated per (session, skill): re-reading a
    long skill across several ``sed`` pages counts once.
    """

    vendor = "codex"

    def __init__(self, home: Path) -> None:
        codex = home / ".codex"
        self._roots = (codex / "sessions", codex / "archived_sessions")
        self.dropped_lines = 0

    def events(self) -> Iterator[SkillEvent]:
        for root in self._roots:
            if not root.is_dir():
                continue
            for jsonl in sorted(root.glob("rollout-*.jsonl")):
                yield from self._read_file(jsonl)

    def _read_file(self, path: Path) -> Iterator[SkillEvent]:
        seen: set[str] = set()
        for raw in _iter_lines(path):
            obj = _decode(raw)
            if obj is None:
                self.dropped_lines += 1
                continue
            yield from _codex_opens(obj, path.stem, seen)


def _codex_opens(obj: dict[str, object], session: str, seen: set[str]) -> Iterator[SkillEvent]:
    payload = _as_dict(obj.get("payload"))
    if payload is None:
        return
    if payload.get("type") != "function_call" or payload.get("name") != "exec_command":
        return
    timestamp = _timestamp(obj)
    if timestamp is None:
        return
    args = _as_str(payload.get("arguments")) or ""
    project = _codex_project(args)
    for name in dict.fromkeys(_SKILL_PATH.findall(args)):
        key = f"{session}:{name}"
        if key not in seen:
            seen.add(key)
            yield SkillEvent(name, "codex", project, timestamp, False, session)


def _codex_project(args: str) -> str:
    parsed = _decode(args)
    workdir = _as_str(parsed.get("workdir")) if parsed else None
    return Path(workdir).name if workdir else "codex"


def _decode(raw: str) -> dict[str, object] | None:
    try:
        return _as_dict(json.loads(raw))
    except json.JSONDecodeError:
        return None


def _iter_lines(path: Path) -> Iterator[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for line in text.splitlines():
        if line.strip():
            yield line


# ---------------------------------------------------------------------------
# Canonical inventory (for dead-skill detection)
# ---------------------------------------------------------------------------


def canonical_skill_names(dotfiles_dir: Path) -> frozenset[str]:
    """Names of every skill that lives in ``ai/skills/*/SKILL.md``."""
    skills_dir = dotfiles_dir / "ai" / "skills"
    if not skills_dir.is_dir():
        return frozenset()
    return frozenset(md.parent.name for md in skills_dir.glob("*/SKILL.md"))


# ---------------------------------------------------------------------------
# Report model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillStat:
    skill: str
    fires: int
    explicit: int
    projects: int
    last_seen: datetime
    buckets: tuple[int, ...]
    canonical: bool

    @property
    def autonomous(self) -> int:
        return self.fires - self.explicit

    @property
    def auto_pct(self) -> int:
        return round(100 * self.autonomous / self.fires) if self.fires else 0

    @property
    def sparkline(self) -> str:
        return _sparkline(self.buckets)

    @property
    def verdict(self) -> str:
        tag = "" if self.canonical else " · other repos"
        if self.fires >= 2 and self.auto_pct >= 50:
            return "✅ healthy" + tag
        if self.auto_pct < 50:
            return "⚠ weak auto-trigger" + tag
        return "· low volume" + tag


@dataclass(frozen=True)
class SkillUsageReport:
    since: datetime
    now: datetime
    total_fires: int
    projects: int
    sessions: int
    leaderboard: tuple[SkillStat, ...]
    dead: tuple[str, ...]
    weak_triggers: tuple[SkillStat, ...]
    sequences: tuple[tuple[tuple[str, str], int], ...]
    vendor_counts: tuple[tuple[str, int], ...]
    dropped_lines: int


# ---------------------------------------------------------------------------
# Aggregation service
# ---------------------------------------------------------------------------


class SkillUsageService:
    """Aggregate ``SkillEvent``s into a ``SkillUsageReport``."""

    def __init__(
        self,
        *,
        home: Path,
        dotfiles_dir: Path,
        readers: Iterable[TranscriptReader] | None = None,
    ) -> None:
        self._home = home
        self._dotfiles_dir = dotfiles_dir
        self._readers: list[TranscriptReader] = (
            list(readers)
            if readers is not None
            else [ClaudeTranscriptReader(home), CodexTranscriptReader(home)]
        )

    def report(self, *, since_days: int, now: datetime) -> SkillUsageReport:
        cutoff = now - timedelta(days=since_days)
        canonical = canonical_skill_names(self._dotfiles_dir)

        events: list[SkillEvent] = []
        dropped = 0
        for reader in self._readers:
            events.extend(reader.events())
            dropped += reader.dropped_lines

        kept = _real_skill_events(events, canonical)
        windowed = [e for e in kept if e.timestamp >= cutoff]
        leaderboard = _leaderboard(windowed, canonical, cutoff, now)
        fired = {e.skill for e in windowed} | {_short(e.skill) for e in windowed}

        return SkillUsageReport(
            since=cutoff,
            now=now,
            total_fires=len(windowed),
            projects=len({e.project for e in windowed}),
            sessions=len({e.session_id for e in windowed}),
            leaderboard=leaderboard,
            dead=tuple(sorted(name for name in canonical if name not in fired)),
            weak_triggers=tuple(
                s for s in leaderboard if s.canonical and s.fires >= 2 and s.auto_pct < 50
            ),
            sequences=_sequences(windowed),
            vendor_counts=tuple(Counter(e.vendor for e in windowed).most_common()),
            dropped_lines=dropped,
        )


def _real_skill_events(events: list[SkillEvent], canonical: frozenset[str]) -> list[SkillEvent]:
    """Drop explicit events that aren't real skills.

    An explicit (slash) event counts only if its name is canonical or it has also
    fired autonomously somewhere — this filters out built-in commands like
    ``/compact`` and ``/login``, which surface as ``<command-name>`` but are not
    skills. Autonomous (model-chosen) events are always kept.
    """
    known = canonical | {_short(e.skill) for e in events if not e.explicit}
    return [e for e in events if not e.explicit or _short(e.skill) in known]


def _leaderboard(
    events: list[SkillEvent],
    canonical: frozenset[str],
    cutoff: datetime,
    now: datetime,
) -> tuple[SkillStat, ...]:
    by_skill: dict[str, list[SkillEvent]] = defaultdict(list)
    for event in events:
        by_skill[event.skill].append(event)

    stats = [
        SkillStat(
            skill=skill,
            fires=len(group),
            explicit=sum(1 for e in group if e.explicit),
            projects=len({e.project for e in group}),
            last_seen=max(e.timestamp for e in group),
            buckets=_bucketize([e.timestamp for e in group], cutoff, now),
            canonical=skill in canonical or _short(skill) in canonical,
        )
        for skill, group in by_skill.items()
    ]
    stats.sort(key=lambda s: (s.fires, s.last_seen), reverse=True)
    return tuple(stats)


def _sequences(events: list[SkillEvent]) -> tuple[tuple[tuple[str, str], int], ...]:
    """Recurring (2 or more) consecutive skill pairs within a session."""
    by_session: dict[str, list[SkillEvent]] = defaultdict(list)
    for event in events:
        by_session[event.session_id].append(event)

    counter: Counter[tuple[str, str]] = Counter()
    for group in by_session.values():
        shorts = [_short(e.skill) for e in sorted(group, key=lambda e: e.timestamp)]
        for first, second in pairwise(shorts):
            if first != second:
                counter[(first, second)] += 1
    return tuple((pair, n) for pair, n in counter.most_common() if n >= 2)


def _bucketize(timestamps: list[datetime], cutoff: datetime, now: datetime) -> tuple[int, ...]:
    """Distribute timestamps across ``_BUCKETS`` even time slots for a sparkline."""
    span = (now - cutoff).total_seconds()
    if span <= 0:
        return (len(timestamps),)
    counts = [0] * _BUCKETS
    for ts in timestamps:
        frac = (ts - cutoff).total_seconds() / span
        idx = min(_BUCKETS - 1, max(0, int(frac * _BUCKETS)))
        counts[idx] += 1
    return tuple(counts)


def _sparkline(buckets: tuple[int, ...]) -> str:
    peak = max(buckets, default=0)
    if peak == 0:
        return _SPARK[0] * len(buckets)
    return "".join(
        _SPARK[min(len(_SPARK) - 1, round(b / peak * (len(_SPARK) - 1)))] for b in buckets
    )
