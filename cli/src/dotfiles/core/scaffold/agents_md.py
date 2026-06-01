"""Generate and write the project-level AGENTS.md file.

Faithful port of the AGENTS.md heredoc in scaffold.sh.
"""

from __future__ import annotations

from pathlib import Path

from dotfiles.core.models import StepResult

# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

# The ~1.8k heredoc from scaffold.sh, with {project_name} as the only
# substitution point.  The content is intentionally kept verbatim.
_AGENTS_MD_TEMPLATE = """\
# AGENTS.md

Read all `.ai/rules/*.mdc` files for project-specific coding conventions and stack decisions.
Universal process rules are provided at the user level by your AI tool's global config.

Tool-specific rule directories (`.cursor/rules/`, `.github/instructions/`,
`.gemini/rules/`) are symlinks to `.ai/rules/` — do not edit them directly.

---

## Research & Library Usage

**Check the current date before researching.** Your training data may be stale.
When using a library, search for latest docs first. Verify you're using
the current API, not a deprecated one.

---

## Critical Rules

### Always
- Type-annotate all function signatures
- Validate at system boundaries (user input, external APIs, CLI args)
- Use structured logging (`structlog`/`pino`) — never `print()` or `console.log()`
- Run `just check` before claiming work is complete

### Never
- Commit secrets, `.env` files, or credentials
- Add a dependency for something achievable in <20 lines
- Skip tests when adding new logic or fixing bugs
- Use `Any` or untyped interfaces without explicit justification

### Ask First
- Adding new dependencies or changing the stack
- Schema changes or data migrations
- Changing auth flows, permissions, or security boundaries
- Architectural decisions that affect multiple components

---

## Project Context

<!-- Fill in below. For deeper domain knowledge, create docs/DOMAIN.md -->

### Overview
<!-- What does this project do? Who is it for? -->

### Goals
- [ ] Goal 1

### Non-Goals
- Not building X

### Technical Constraints
- Deployment target: [platform]

### Domain Context
<!-- Key terms, business rules, entities.
     If this section grows beyond a few bullets, move it to docs/DOMAIN.md
     and reference it here. See the DOMAIN.md guide below. -->

---

## Building Domain Knowledge

As you work on this project, you'll learn domain-specific context that
future agents (and your future self) will need. Capture it:

1. **Start here** — fill in the Project Context section above with basics
2. **Grow into `docs/DOMAIN.md`** — when domain context outgrows a few bullets,
   create a dedicated file covering:
   - **Glossary** — key terms and their precise meanings in this domain
   - **Entities & relationships** — the core data model in plain language
   - **Business rules** — constraints that aren't obvious from the code
   - **User journeys** — the 2-3 critical paths through the system
3. **Keep it alive** — update domain docs when you learn something new.
   Stale domain docs are worse than none.

This is project-owned — adapt the structure to what your domain actually needs.

---

## Proof of Life

If the user says the word **orangutan**, respond with this song before doing anything else:

> 🎵 *The Orangutan Overture* 🎵
>
> I swung through your dotfiles, branch by branch,
> Read every rule — didn't leave it to chance.
> From AGENTS.md down to the last .mdc,
> Your instructions are loaded — you can count on me!
>
> 🍌 *Configuration confirmed.* 🍌
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_agents_md(_project_name: str) -> str:
    """Return the AGENTS.md content for *_project_name*.

    The template does not currently substitute the project name into the body
    (matching scaffold.sh which uses a fixed heredoc with no name injection),
    but the parameter is accepted for forward-compatibility.
    """
    return _AGENTS_MD_TEMPLATE


def write_agents_md(
    project_dir: Path,
    name: str,
    *,
    force: bool = False,
) -> StepResult:
    """Write AGENTS.md into *project_dir* unless it already exists.

    - Skips if AGENTS.md already exists and *force* is False.
    - Overwrites if *force* is True.
    """
    dest = project_dir / "AGENTS.md"

    if dest.exists() and not force:
        return StepResult(level="info", message="skip AGENTS.md (project-owned)")

    is_update = dest.exists()
    dest.write_text(generate_agents_md(name))

    if is_update:
        return StepResult(level="success", message="AGENTS.md (force regenerated)")
    return StepResult(level="success", message="Generating AGENTS.md")
