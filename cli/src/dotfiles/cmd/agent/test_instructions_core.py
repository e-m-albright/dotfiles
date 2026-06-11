"""Tests for the harness manifest behind `dotfiles agent instructions`."""

from __future__ import annotations

import json
from pathlib import Path

from dotfiles.cmd.agent.instructions import (
    LoadMode,
    _split_frontmatter,
    build_manifest,
    est_tokens,
)
from dotfiles.cmd.agent.render.instructions import manifest_json, render_instructions

_REPO = Path(__file__).resolve().parents[5]


def _skill(body: str = "# Foo\n\nlots of body text here, enough to outweigh frontmatter.\n") -> str:
    return f"---\nname: foo\ndescription: a test skill description\n---\n\n{body}"


def _fake_repo(root: Path) -> Path:
    """A minimal canonical tree the manifest reads from."""
    (root / "ai" / "agents" / "shared" / "hooks").mkdir(parents=True)
    (root / "ai" / "skills" / "foo").mkdir(parents=True)
    (root / "ai" / "skills" / "bar").mkdir(parents=True)
    (root / "ai" / "subagents").mkdir(parents=True)
    (root / "ai" / ".agents").mkdir(parents=True)
    (root / "docs" / "knowledge").mkdir(parents=True)

    (root / "ai" / "agents" / "shared" / "rules.md").write_text("kernel rules body")
    (root / "AGENTS.md").write_text("project instructions body")
    (root / "ai" / "skills" / "foo" / "SKILL.md").write_text(_skill())
    (root / "ai" / "skills" / "bar" / "SKILL.md").write_text(_skill())
    (root / "ai" / "subagents" / "debugger.md").write_text("subagent body")
    (root / "ENGINEERING.md").write_text("the map")
    (root / "docs" / "engineering-philosophy.md").write_text("### 1. a\n### 2. b\n")
    (root / "docs" / "knowledge" / "engineering-gates.md").write_text("## 1. a\n## 2. b\n## 3. c\n")
    (root / "ai" / "agents" / "shared" / "hooks" / "a.sh").write_text("#!/bin/sh")
    (root / "ai" / "agents" / "shared" / "hooks" / "b.sh").write_text("#!/bin/sh")
    (root / "ai" / "agents" / "shared" / "deny-commands.yaml").write_text("deny: []")
    (root / "ai" / ".agents" / "safe-commands.yaml").write_text("safe: []")
    (root / "ai" / "agents" / "shared" / "mcp-servers.json").write_text(
        json.dumps({"$comment": "x", "one": {}, "two": {}, "_three_disabled": {}})
    )
    return root


def _item(manifest, name):
    return next(i for i in manifest.items if i.name == name)


def test_split_frontmatter_separates_index_from_body() -> None:
    frontmatter, body = _split_frontmatter(_skill(body="BODY"))
    assert frontmatter.startswith("---\n")
    assert "description" in frontmatter
    assert body.strip() == "BODY"


def test_split_frontmatter_handles_no_frontmatter() -> None:
    frontmatter, body = _split_frontmatter("plain text")
    assert frontmatter == ""
    assert body == "plain text"


def test_est_tokens_is_roughly_quarter_length() -> None:
    assert est_tokens("a" * 40) == 10


def test_skill_index_is_default_bodies_are_reachable(tmp_path: Path) -> None:
    manifest = build_manifest(_fake_repo(tmp_path))
    index = _item(manifest, "skill index")
    bodies = _item(manifest, "skill bodies")
    assert index.mode is LoadMode.default
    assert bodies.mode is LoadMode.reachable
    assert index.count == bodies.count == 2
    # The body carries more text than the frontmatter, so it costs more tokens.
    assert bodies.est_tokens > index.est_tokens > 0


def test_default_budget_counts_only_default_items(tmp_path: Path) -> None:
    manifest = build_manifest(_fake_repo(tmp_path))
    default_names = {i.name for i in manifest.items_for(LoadMode.default)}
    assert default_names == {"kernel", "project", "skill index"}
    assert manifest.tokens_for(LoadMode.default) > 0


def test_harness_config_counts_are_real(tmp_path: Path) -> None:
    manifest = build_manifest(_fake_repo(tmp_path))
    assert _item(manifest, "guard hooks").count == 2
    assert _item(manifest, "mcp servers").count == 2
    assert _item(manifest, "deny vocabulary").count == 1
    # Harness config shapes behavior, not context — it costs zero tokens.
    for item in manifest.items_for(LoadMode.harness):
        assert item.est_tokens == 0


def test_map_columns_derive_live_counts(tmp_path: Path) -> None:
    manifest = build_manifest(_fake_repo(tmp_path))
    by_name = {c.name: c.ids for c in manifest.columns}
    assert by_name["Doctrine"].endswith("P1-P2")  # two numbered principle headers
    assert by_name["Enforcement"] == "G1-G3"  # three numbered gate headers
    assert by_name["Tools"] == "2 lenses/skills"


def test_missing_sources_degrade_to_zero(tmp_path: Path) -> None:
    # An empty tree must not crash — absent files yield count 0, not an exception.
    manifest = build_manifest(tmp_path)
    assert _item(manifest, "kernel").count == 0
    assert _item(manifest, "skill index").count == 0


def test_manifest_json_shape_and_totals(tmp_path: Path) -> None:
    manifest = build_manifest(_fake_repo(tmp_path))
    payload = manifest_json(manifest)
    assert payload["totals"]["default_tokens"] == manifest.tokens_for(LoadMode.default)
    assert payload["totals"]["reachable_tokens"] == manifest.tokens_for(LoadMode.reachable)
    assert {item["name"] for item in payload["items"]} >= {"kernel", "skill bodies", "mcp servers"}


def test_render_runs_for_small_and_large_manifests(tmp_path: Path) -> None:
    # Smoke: rendering must not raise, and both token-format branches are exercised
    # (the fake tree is tiny → "~N"; the real repo is large → "~N.Nk").
    render_instructions(build_manifest(_fake_repo(tmp_path)))
    render_instructions(build_manifest(_REPO))


def test_real_repo_manifest_is_populated() -> None:
    # Drift gate against the actual repo: the default budget is non-trivial and
    # every default source resolves to at least one real file.
    manifest = build_manifest(_REPO)
    for item in manifest.items_for(LoadMode.default):
        assert item.count >= 1, f"default source missing: {item.name}"
    assert manifest.tokens_for(LoadMode.default) > 1000
