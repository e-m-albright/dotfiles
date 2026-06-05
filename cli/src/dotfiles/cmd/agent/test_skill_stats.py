"""Tests for `agent stats` — skill-usage analytics mined from transcripts."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from typer.testing import CliRunner

from dotfiles.app.main import app
from dotfiles.cmd.agent.skill_stats import ClaudeTranscriptReader, SkillUsageService
from dotfiles.testing.fakes import make_fake_context

runner = CliRunner()

NOW = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)


def _at(offset_seconds: int) -> datetime:
    return NOW + timedelta(seconds=offset_seconds)


def _user_slash(skill: str, *, ts: datetime, session: str = "s1", proj: str = "/x/proj") -> str:
    return json.dumps(
        {
            "type": "user",
            "timestamp": ts.isoformat(),
            "sessionId": session,
            "cwd": proj,
            "message": {"role": "user", "content": f"<command-name>/{skill}</command-name>"},
        }
    )


def _user_text(text: str, *, ts: datetime, session: str = "s1", proj: str = "/x/proj") -> str:
    return json.dumps(
        {
            "type": "user",
            "timestamp": ts.isoformat(),
            "sessionId": session,
            "cwd": proj,
            "message": {"role": "user", "content": text},
        }
    )


def _assistant_skill(
    skill: str, *, ts: datetime, session: str = "s1", proj: str = "/x/proj"
) -> str:
    return json.dumps(
        {
            "type": "assistant",
            "timestamp": ts.isoformat(),
            "sessionId": session,
            "cwd": proj,
            "message": {
                "role": "assistant",
                "content": [{"type": "tool_use", "name": "Skill", "input": {"skill": skill}}],
            },
        }
    )


def _write_session(home: Path, name: str, lines: list[str], project: str = "proj") -> None:
    folder = home / ".claude" / "projects" / project
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.jsonl").write_text("\n".join(lines) + "\n")


def _dotfiles_with_skills(base: Path, *names: str) -> Path:
    dotfiles = base / "dotfiles"
    for name in names:
        skill_dir = dotfiles / "ai" / "skills" / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\n# {name}\n")
    return dotfiles


# ---------------------------------------------------------------------------
# Reader — explicit vs autonomous classification
# ---------------------------------------------------------------------------


def test_reader_explicit_slash_autonomous_tool_use(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _write_session(
        home,
        "s1",
        [
            _user_slash("code-review", ts=_at(0)),  # explicit: you typed it
            _assistant_skill("brainstorming", ts=_at(1)),  # autonomous: model chose it
        ],
    )

    events = {e.skill: e for e in ClaudeTranscriptReader(home).events()}

    assert events["code-review"].explicit is True
    assert events["brainstorming"].explicit is False


def test_reader_emits_both_sources_for_same_skill(tmp_path: Path) -> None:
    # A slash invocation and an autonomous tool_use of the same skill are two
    # distinct invocations, not one double-counted.
    home = tmp_path / "home"
    _write_session(
        home,
        "s1",
        [_user_slash("code-review", ts=_at(0)), _assistant_skill("code-review", ts=_at(1))],
    )

    explicit = sorted(e.explicit for e in ClaudeTranscriptReader(home).events())

    assert explicit == [False, True]


def test_reader_counts_malformed_lines(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _write_session(home, "s1", ["{not valid json", _assistant_skill("code-review", ts=_at(0))])

    reader = ClaudeTranscriptReader(home)
    events = list(reader.events())

    assert len(events) == 1
    assert reader.dropped_lines == 1


def test_reader_missing_projects_dir_is_empty(tmp_path: Path) -> None:
    assert list(ClaudeTranscriptReader(tmp_path / "nope").events()) == []


# ---------------------------------------------------------------------------
# Service — dead skills, weak triggers, windowing, sequences
# ---------------------------------------------------------------------------


def _service(home: Path, dotfiles: Path) -> SkillUsageService:
    return SkillUsageService(home=home, dotfiles_dir=dotfiles)


def test_dead_skills_are_canonical_with_zero_fires(tmp_path: Path) -> None:
    home = tmp_path / "home"
    dotfiles = _dotfiles_with_skills(tmp_path, "code-review", "premerge-review")
    _write_session(
        home,
        "s1",
        [_user_text("review this", ts=_at(0)), _assistant_skill("code-review", ts=_at(1))],
    )

    report = _service(home, dotfiles).report(since_days=90, now=_at(60))

    assert "premerge-review" in report.dead
    assert "code-review" not in report.dead


def test_weak_trigger_flags_explicit_only_skill(tmp_path: Path) -> None:
    home = tmp_path / "home"
    dotfiles = _dotfiles_with_skills(tmp_path, "code-review")
    _write_session(
        home,
        "s1",
        [_user_slash("code-review", ts=_at(0)), _user_slash("code-review", ts=_at(2))],
    )

    report = _service(home, dotfiles).report(since_days=90, now=_at(60))

    weak = {s.skill for s in report.weak_triggers}
    assert "code-review" in weak


def test_builtin_slashes_are_filtered(tmp_path: Path) -> None:
    home = tmp_path / "home"
    dotfiles = _dotfiles_with_skills(tmp_path, "code-review")
    _write_session(
        home,
        "s1",
        [
            _user_slash("compact", ts=_at(0)),  # built-in command, not a skill
            _assistant_skill("code-review", ts=_at(1)),
        ],
    )

    report = _service(home, dotfiles).report(since_days=90, now=_at(60))

    skills = {s.skill for s in report.leaderboard}
    assert "compact" not in skills
    assert "code-review" in skills


def test_slash_only_skill_is_weak_not_dead(tmp_path: Path) -> None:
    home = tmp_path / "home"
    dotfiles = _dotfiles_with_skills(tmp_path, "improve-codebase-architecture")
    _write_session(
        home,
        "s1",
        [
            _user_slash("improve-codebase-architecture", ts=_at(0)),
            _user_slash("improve-codebase-architecture", ts=_at(2)),
        ],
    )

    report = _service(home, dotfiles).report(since_days=90, now=_at(60))

    assert "improve-codebase-architecture" not in report.dead
    assert "improve-codebase-architecture" in {s.skill for s in report.weak_triggers}


def test_windowing_excludes_old_events(tmp_path: Path) -> None:
    home = tmp_path / "home"
    dotfiles = _dotfiles_with_skills(tmp_path, "code-review")
    old = NOW - timedelta(days=100)
    _write_session(
        home,
        "s1",
        [_assistant_skill("code-review", ts=old, session="old")],
    )

    report = _service(home, dotfiles).report(since_days=90, now=NOW)

    assert report.total_fires == 0
    assert "code-review" in report.dead  # no fire in window → counts as dead


def test_sequences_detects_recurring_chains(tmp_path: Path) -> None:
    home = tmp_path / "home"
    dotfiles = _dotfiles_with_skills(tmp_path, "brainstorming", "writing-plans")
    for session in ("s1", "s2"):
        _write_session(
            home,
            session,
            [
                _assistant_skill("brainstorming", ts=_at(0), session=session),
                _assistant_skill("writing-plans", ts=_at(1), session=session),
            ],
        )

    report = _service(home, dotfiles).report(since_days=90, now=_at(60))

    assert (("brainstorming", "writing-plans"), 2) in report.sequences


# ---------------------------------------------------------------------------
# CLI — smoke + JSON
# ---------------------------------------------------------------------------


def _recent_session(home: Path) -> None:
    recent = datetime.now(UTC) - timedelta(days=1)
    _write_session(
        home,
        "s1",
        [
            _user_slash("code-review", ts=recent),
            _assistant_skill("code-review", ts=recent + timedelta(seconds=1)),
        ],
    )


def test_cli_stats_renders_report(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _recent_session(home)
    dotfiles = _dotfiles_with_skills(tmp_path, "code-review", "premerge-review")
    ctx = make_fake_context(home=home, dotfiles_dir=dotfiles)

    result = runner.invoke(app, ["agent", "stats"], obj=ctx)

    assert result.exit_code == 0
    assert "Skill Usage" in result.output
    assert "code-review" in result.output


def test_cli_stats_json(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _recent_session(home)
    dotfiles = _dotfiles_with_skills(tmp_path, "code-review", "premerge-review")
    ctx = make_fake_context(home=home, dotfiles_dir=dotfiles)

    result = runner.invoke(app, ["agent", "stats", "--json"], obj=ctx)

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total_fires"] >= 1
    assert "premerge-review" in data["dead"]
