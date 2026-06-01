"""Deploy optional scaffold bundles into a project.

Faithful port of the --with-audit-pipeline / --with-baselines /
--with-agent-rules-sync blocks in scaffold.sh.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from dotfiles.core.models import StepResult

_SCAFFOLDS_REL = "prompts/scaffolds"


def _deploy_scaffold_files(
    dotfiles_dir: Path,
    project_dir: Path,
    scaffold_name: str,
    files: list[str],
    *,
    force: bool = False,
    executable: bool = False,
) -> list[StepResult]:
    """Copy a list of relative file paths from a scaffold bundle into the project.

    Each path in *files* is relative to both the source scaffold dir and the
    project root.  Returns StepResults for each file.
    """
    src_base = dotfiles_dir / _SCAFFOLDS_REL / scaffold_name
    results: list[StepResult] = []

    for rel in files:
        src = src_base / rel
        dest = project_dir / rel

        if dest.is_file() and not force:
            results.append(StepResult(level="info", message=f"skip {rel}"))
            continue

        if not src.is_file():
            results.append(StepResult(level="warn", message=f"source not found: {rel}"))
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        if executable:
            dest.chmod(dest.stat().st_mode | 0o111)
        results.append(StepResult(level="success", message=f"Deployed {rel}"))

    return results


def deploy_audit_pipeline(
    dotfiles_dir: Path,
    project_dir: Path,
    *,
    force: bool = False,
) -> list[StepResult]:
    """Deploy the audit-pipeline scaffold (--with-audit-pipeline).

    Copies: scripts/audit/security.sh, scripts/audit/ai_usage.py,
    just/audit/mod.just, .ai/prompts/audits/security.md,
    .ai/prompts/audits/ai-usage.md
    """
    files = [
        "scripts/audit/security.sh",
        "scripts/audit/ai_usage.py",
        "just/audit/mod.just",
        ".ai/prompts/audits/security.md",
        ".ai/prompts/audits/ai-usage.md",
    ]
    return _deploy_scaffold_files(
        dotfiles_dir,
        project_dir,
        "audit-pipeline",
        files,
        force=force,
        executable=True,
    )


def deploy_baselines(
    dotfiles_dir: Path,
    project_dir: Path,
    *,
    force: bool = False,
) -> list[StepResult]:
    """Deploy the baselines scaffold (--with-baselines).

    Copies: baselines.json, scripts/check_baselines.py.
    Also copies lefthook.baselines.yml if absent (never forced).
    """
    results = _deploy_scaffold_files(
        dotfiles_dir,
        project_dir,
        "baselines",
        ["baselines.json", "scripts/check_baselines.py"],
        force=force,
        executable=True,
    )

    # lefthook fragment — only once, never forced (mirrors scaffold.sh)
    lh_src = dotfiles_dir / _SCAFFOLDS_REL / "baselines" / "lefthook.baselines.yml"
    lh_dest = project_dir / "lefthook.baselines.yml"
    if not lh_dest.is_file() and lh_src.is_file():
        shutil.copy2(lh_src, lh_dest)
        results.append(
            StepResult(
                level="success",
                message="Deployed lefthook.baselines.yml (fragment — merge into lefthook.yml)",
            )
        )

    return results


def deploy_agent_rules_sync(
    dotfiles_dir: Path,
    project_dir: Path,
    *,
    force: bool = False,
) -> list[StepResult]:
    """Deploy the agent-rules-sync scaffold (--with-agent-rules-sync).

    Copies: scripts/sync-agent-rules.sh.
    Also copies lefthook.agent-rules.yml if absent (never forced).
    """
    results = _deploy_scaffold_files(
        dotfiles_dir,
        project_dir,
        "agent-rules-sync",
        ["scripts/sync-agent-rules.sh"],
        force=force,
        executable=True,
    )

    lh_src = dotfiles_dir / _SCAFFOLDS_REL / "agent-rules-sync" / "lefthook.agent-rules.yml"
    lh_dest = project_dir / "lefthook.agent-rules.yml"
    if not lh_dest.is_file() and lh_src.is_file():
        shutil.copy2(lh_src, lh_dest)
        results.append(
            StepResult(
                level="success",
                message="Deployed lefthook.agent-rules.yml (fragment — merge into lefthook.yml)",
            )
        )

    return results
