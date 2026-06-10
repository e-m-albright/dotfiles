import json
from pathlib import Path

from dotfiles.cmd.agent.skill_inventory import inventory
from dotfiles.testing.fakes import FakeProcessRunner, write_tree


def _git_history(dotfiles: Path, *paths: str) -> FakeProcessRunner:
    runner = FakeProcessRunner()
    runner.script(
        ("git", "-C", str(dotfiles), "log", "--all", "--pretty=format:", "--name-only"),
        stdout="\n".join(paths),
    )
    return runner


def _skill_md(desc: str) -> str:
    return f"---\nname: x\ndescription: {desc}\n---\n\nbody\n"


def test_inventory_classifies_origin_and_reads_description(tmp_path: Path) -> None:
    dotfiles = tmp_path / "dotfiles"
    write_tree(
        dotfiles,
        {
            "ai/skills/converge/SKILL.md": _skill_md("Drive a codebase toward simpler code"),
            "ai/agents/claude/external-skills.txt": "hairyf/skills@tauri\n",
        },
    )
    home = tmp_path / "home"
    write_tree(
        home,
        {
            # external (tracked) — deployed copy carries the description
            ".claude/skills/tauri/SKILL.md": _skill_md("Cross-platform app toolkit"),
            # untracked — deployed in a shared dir, in neither canonical nor external
            ".agents/skills/vitest/SKILL.md": _skill_md("Vitest test framework"),
            # retired — was ours (in git history below), since removed
            ".agents/skills/legible/SKILL.md": _skill_md("old lens"),
            # builtin — lives only in a vendor's own dir
            ".cursor/skills-cursor/statusline/SKILL.md": _skill_md("Cursor statusline"),
            # a plugin shipping a skill
            ".claude/plugins/installed_plugins.json": json.dumps(
                {
                    "plugins": {
                        "superpowers@official": [
                            {"installPath": str(tmp_path / "plug" / "superpowers")}
                        ]
                    }
                }
            ),
        },
    )
    write_tree(
        tmp_path / "plug" / "superpowers",
        {"skills/brainstorming/SKILL.md": _skill_md("Turn ideas into designs")},
    )

    runner = _git_history(dotfiles, ".ai/skills/legible/SKILL.md")
    by_name = {s.name: s for s in inventory(runner, home, dotfiles)}

    assert by_name["converge"].origin == "canonical"
    assert by_name["converge"].description == "Drive a codebase toward simpler code"
    assert by_name["tauri"].origin == "external"
    assert by_name["tauri"].description == "Cross-platform app toolkit"
    assert by_name["vitest"].origin == "untracked"
    assert by_name["legible"].origin == "retired"  # in git history, not canonical
    assert by_name["statusline"].origin == "builtin"  # only in .cursor/skills-cursor
    assert by_name["brainstorming"].origin == "plugin"
    assert by_name["brainstorming"].source == "superpowers@official"


def test_inventory_is_alphabetical(tmp_path: Path) -> None:
    dotfiles = tmp_path / "dotfiles"
    write_tree(
        dotfiles,
        {
            "ai/skills/zebra/SKILL.md": _skill_md("z"),
            "ai/skills/alpha/SKILL.md": _skill_md("a"),
            "ai/agents/claude/external-skills.txt": "",
        },
    )
    runner = _git_history(dotfiles)
    names = [s.name for s in inventory(runner, tmp_path / "home", dotfiles)]
    assert names == ["alpha", "zebra"]


def test_description_resolves_block_scalars_and_falls_back(tmp_path: Path) -> None:
    """Block-scalar descriptions (`|`/`>`) resolve to their text, collapsed to one
    line; frontmatter too loose for YAML falls back to the first description line."""
    from dotfiles.cmd.agent.skill_inventory import description

    def md(name: str, frontmatter: str) -> Path:
        p = tmp_path / name
        p.write_text(f"---\nname: x\n{frontmatter}\n---\n\nbody\n")
        return p

    literal = md(
        "LITERAL.md", "description: |\n  Builds remote MCP servers\n  with OAuth and deploy."
    )
    assert description(literal) == "Builds remote MCP servers with OAuth and deploy."

    folded = md("FOLDED.md", "description: >-\n  Create a hook for\n  the harness.")
    assert description(folded) == "Create a hook for the harness."

    plain = md("PLAIN.md", "description: Just a normal one-liner.")
    assert description(plain) == "Just a normal one-liner."

    # Unquoted ': ' mid-value is invalid YAML (reads as a nested map) — regex fallback.
    loose = md("LOOSE.md", "description: net LOC: goes down, features removed.")
    assert description(loose) == "net LOC: goes down, features removed."
