"""Create .ai/artifacts/ subdirectory tree with seed files.

Faithful port of the .ai/artifacts/ block in scaffold.sh.
"""

from __future__ import annotations

from pathlib import Path

_SUBDIRS = ("plans", "research", "decisions", "sessions")

_README_CONTENT = """\
# Working Files

All intermediate agent output goes here — never scatter files in the project root.

```
.ai/artifacts/
├── plans/        # Implementation plans (gitignored)
├── research/     # Investigation notes (gitignored)
├── decisions/    # Architecture Decision Records (versioned, committed)
└── sessions/     # Conversation logs (gitignored)
```

## Conventions

- Date-prefix all files: `YYYY-MM-DD-description.md`
- Only `decisions/` is committed to git — everything else is ephemeral
- Domain docs belong in `docs/` (versioned), not here
- Clean up files when incorporated or abandoned
"""

_DECISIONS_INDEX_CONTENT = """\
# Architecture Decision Records

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| — | (none yet) | — | — |
"""


def create_artifacts_dir(project_dir: Path) -> None:
    """Create .ai/artifacts/ subdirs and seed files under *project_dir*.

    Idempotent — skips existing files/dirs.
    """
    artifacts = project_dir / ".ai" / "artifacts"
    for subdir in _SUBDIRS:
        (artifacts / subdir).mkdir(parents=True, exist_ok=True)

    readme = artifacts / "README.md"
    if not readme.is_file():
        readme.write_text(_README_CONTENT)

    decisions_index = artifacts / "decisions" / "_index.md"
    if not decisions_index.is_file():
        decisions_index.write_text(_DECISIONS_INDEX_CONTENT)
