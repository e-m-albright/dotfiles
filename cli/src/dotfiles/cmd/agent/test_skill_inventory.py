import json
from pathlib import Path

from dotfiles.cmd.agent.skill_inventory import inventory
from dotfiles.testing.fakes import write_tree


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
            # untracked — deployed, in neither canonical nor external
            ".agents/skills/vitest/SKILL.md": _skill_md("Vitest test framework"),
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

    by_name = {s.name: s for s in inventory(home, dotfiles)}

    assert by_name["converge"].origin == "canonical"
    assert by_name["converge"].description == "Drive a codebase toward simpler code"
    assert by_name["tauri"].origin == "external"
    assert by_name["tauri"].description == "Cross-platform app toolkit"
    assert by_name["vitest"].origin == "untracked"
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
    names = [s.name for s in inventory(tmp_path / "home", dotfiles)]
    assert names == ["alpha", "zebra"]
