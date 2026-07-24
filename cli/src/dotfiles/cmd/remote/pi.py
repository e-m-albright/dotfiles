"""Launch pi in a project-specific Zellij session for phone workflows."""

import json
import re
from pathlib import Path

_PROJECT_ROOTS = ("public", "private")


def resolve_project(home: Path, value: str) -> Path:
    """Resolve an absolute path or an unambiguous repo basename under ~/code."""
    supplied = Path(value).expanduser()
    if supplied.is_absolute():
        if supplied.is_dir():
            return supplied.resolve()
        raise ValueError(f"project not found: {value}")

    matches = [
        candidate.resolve()
        for scope in _PROJECT_ROOTS
        if (candidate := home / "code" / scope / value).is_dir()
    ]
    if not matches:
        raise ValueError(f"project not found under ~/code/public or ~/code/private: {value}")
    if len(matches) > 1:
        raise ValueError(f"project name is ambiguous; pass its absolute path: {value}")
    return matches[0]


def session_name_for(project: Path) -> str:
    """Return a stable, Zellij-safe session name for a project."""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", project.name).strip("-")
    if not slug:
        raise ValueError(f"project basename cannot form a session name: {project.name}")
    return f"pi-{slug}"


def project_layout(project: Path, session_name: str) -> str:
    """Build the one-pane mobile layout used when a project session is first created."""
    cwd = json.dumps(str(project))
    tab_name = json.dumps(session_name)
    command = json.dumps("pi --continue; exec /bin/zsh -l")
    return f"""layout {{
    default_tab_template {{
        children
        pane size=1 borderless=true {{
            plugin location="zellij:compact-bar"
        }}
    }}
    tab name={tab_name} focus=true {{
        pane command="/bin/zsh" cwd={cwd} {{
            args "-lc" {command}
        }}
    }}
}}
"""
