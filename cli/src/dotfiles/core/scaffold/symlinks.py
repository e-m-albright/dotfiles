"""Tool-rule symlinks and root symlinks (e.g. CODEX.md → AGENTS.md).

Faithful port of _symlink_rules_for_tool() / setup_tool_symlinks() /
generate_root_symlinks() from scaffold.sh.

Key invariant: symlink targets are constructed by STRING CONCATENATION of
the registry's symlinkPrefix with ".ai/rules/<name>.mdc" — NOT os.path.relpath.
This matches the bash: ``ln -s "${prefix}.ai/rules/$rule_name" "$tool_link"``
"""

from __future__ import annotations

from pathlib import Path

from dotfiles.core.scaffold.tool_registry import ToolTarget


def _symlink_rules_for_tool(
    project_dir: Path,
    rules_dir: str,
    suffix: str,
    prefix: str,
) -> None:
    """Create symlinks in <project_dir>/<rules_dir>/ pointing to .ai/rules/ files.

    For each *.mdc file already present in project_dir/.ai/rules/:
      - Compute target filename: same base name + tool suffix
      - Symlink target string: ``<prefix>.ai/rules/<name>.mdc``
        (prefix is taken verbatim from the registry, e.g. "../../")
      - Idempotent: skip if symlink already points at the right target;
        remove and recreate if it points somewhere else or is a plain file
        (mirroring the FORCE-agnostic symlink refresh in scaffold.sh —
        scaffold.sh ALWAYS refreshes symlinks regardless of --force).

    No return value — symlink creation side-effects only.
    """
    tool_rules_dir = project_dir / rules_dir
    tool_rules_dir.mkdir(parents=True, exist_ok=True)

    ai_rules_dir = project_dir / ".ai" / "rules"
    if not ai_rules_dir.is_dir():
        return

    for rule_file in sorted(ai_rules_dir.glob("*.mdc")):
        rule_name = rule_file.name
        base_name = rule_file.stem

        # Target filename: use the tool's expected suffix
        target_name = rule_name if suffix == ".mdc" else base_name + suffix

        tool_link = tool_rules_dir / target_name
        expected_target = f"{prefix}.ai/rules/{rule_name}"

        if tool_link.is_symlink():
            current_target = str(tool_link.readlink())
            if current_target == expected_target:
                continue  # already correct
            tool_link.unlink()
        elif tool_link.exists():
            # Plain file: remove it (scaffold.sh removes it with FORCE check,
            # but symlink refresh always happens in the non-FORCE path too)
            tool_link.unlink()

        tool_link.symlink_to(expected_target)


def setup_tool_symlinks(
    project_dir: Path,
    tools: dict[str, ToolTarget],
) -> None:
    """Set up tool-specific rule symlinks for all tools in *tools*.

    Individual ToolTarget entries supply rules_dir / suffix / symlink_prefix.
    Symlinks are refreshed from whatever *.mdc files are present in
    project_dir/.ai/rules/ (matching the bash behaviour).
    """
    for tool_target in tools.values():
        if (
            tool_target.rules_dir is None
            or tool_target.suffix is None
            or tool_target.symlink_prefix is None
        ):
            continue
        _symlink_rules_for_tool(
            project_dir,
            tool_target.rules_dir,
            tool_target.suffix,
            tool_target.symlink_prefix,
        )


_AGENTS_MD = "AGENTS.md"


def _maybe_create_root_symlink(link_path: Path, *, force: bool) -> bool:
    """Try to create/refresh a root symlink pointing to AGENTS.md.

    Returns True if the symlink was created (new or force-replaced).
    """
    if link_path.is_symlink() and str(link_path.readlink()) == _AGENTS_MD:
        return False  # already correct
    if link_path.exists() or link_path.is_symlink():
        if not force:
            return False  # project-owned, don't overwrite
        link_path.unlink()
    link_path.symlink_to(_AGENTS_MD)
    return True


def generate_root_symlinks(
    project_dir: Path,
    tools: dict[str, ToolTarget],
    *,
    force: bool = False,
) -> list[str]:
    """Create root-level symlinks (e.g. CODEX.md → AGENTS.md).

    Mirrors generate_root_symlinks() in scaffold.sh.
    Returns a list of created symlink names for reporting.
    """
    created: list[str] = []
    for tool_target in tools.values():
        root_file = tool_target.root_file
        if root_file is None:
            continue
        if _maybe_create_root_symlink(project_dir / root_file, force=force):
            created.append(root_file)
    return created
