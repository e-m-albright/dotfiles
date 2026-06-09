"""agent_setup.claude — port of agents/claude/setup.sh.

Configures Claude Code:
  - Write the core agent instructions (agents/shared/rules.md) → ~/.claude/CLAUDE.md
  - Prune dangling ~/.claude/rules symlinks (orphans from the bash-era setup)
  - Merge marketplaces (marketplaces.json → settings.json:.extraKnownMarketplaces)
  - Merge plugins (plugins.yaml → settings.json:.enabledPlugins)
  - Replace permissions (permissions.json → settings.json:.permissions)
  - Replace hooks (hooks.json → settings.json:.hooks)
  - Set statusline (statusline.sh → settings.json:.statusLine)
  - Set preferences (voiceEnabled, preferredNotifChannel, defaultMode)
  - Merge MCP servers into ~/.claude.json (.mcpServers)
  - Merge MCP servers + desktop-preferences into ~/Library/.../claude_desktop_config.json
    (http type rewrites to npx -y mcp-remote stdio bridge)
  - deploy_skills(claude-code) + external-skills.txt
  - deploy_subagents
  - clean=True: prune nonconforming plugins/marketplaces/stale mcp__ perms/stale projects

All paths injected; Path.home() MUST NOT appear here.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from dotfiles.adapters.ports import ProcessRunner
from dotfiles.cmd.agent.lib import (
    StepResult,
    all_mcp_server_names,
    build_global_instructions,
    deploy_skills,
    deploy_subagents,
    mcp_servers_for,
    mcp_skip,
    merge_managed_mcp,
)
from dotfiles.cmd.agent.settings_merger import (
    load_json_or,
    merge_replace,
    write_json_safely,
)
from dotfiles.fsutil import prune_broken_symlinks

_JsonDict = dict[str, Any]

# Desktop app config path (relative to home)
_DESKTOP_CONFIG_REL = "Library/Application Support/Claude/claude_desktop_config.json"


def setup_claude(
    *,
    runner: ProcessRunner,
    home: Path,
    dotfiles_dir: Path,
    which: Callable[[str], str | None] = shutil.which,
    clean: bool = False,
    reset_mcp: bool = False,
) -> list[StepResult]:
    """Configure Claude Code. Returns a list of StepResult (one per step)."""
    claude_home = home / ".claude"
    claude_home.mkdir(parents=True, exist_ok=True)

    results: list[StepResult] = []

    if clean:
        results.extend(_setup_clean(dotfiles_dir, home, claude_home))

    results.extend(_setup_instructions(dotfiles_dir, claude_home))
    results.extend(_setup_rules(claude_home))
    results.extend(_setup_marketplaces(dotfiles_dir, claude_home))
    results.extend(_setup_plugins(dotfiles_dir, claude_home))
    results.extend(_setup_permissions(dotfiles_dir, claude_home))
    results.extend(_setup_mcp(dotfiles_dir, home, claude_home, reset_mcp=reset_mcp))
    results.extend(_setup_desktop(dotfiles_dir, home, reset_mcp=reset_mcp))
    results.extend(_setup_hooks(dotfiles_dir, claude_home))
    results.extend(_setup_skills(runner, dotfiles_dir, home, which=which))
    results.extend(deploy_subagents(dotfiles_dir, claude_home / "agents"))
    results.extend(_setup_statusline(dotfiles_dir, claude_home))
    results.extend(_setup_preferences(claude_home))

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _settings_path(claude_home: Path) -> Path:
    return claude_home / "settings.json"


def _load_settings(claude_home: Path) -> _JsonDict:
    return load_json_or(_settings_path(claude_home), {})


def _save_settings(claude_home: Path, data: _JsonDict) -> None:
    write_json_safely(_settings_path(claude_home), data)


def _setup_instructions(dotfiles_dir: Path, claude_home: Path) -> list[StepResult]:
    """Write the core agent instructions → ~/.claude/CLAUDE.md."""
    content = build_global_instructions(dotfiles_dir)
    if content is None:
        return [StepResult(level="error", message="No agents/shared/rules.md found")]
    (claude_home / "CLAUDE.md").write_text(content, encoding="utf-8")
    return [StepResult(level="success", message="Core instructions (~/.claude/CLAUDE.md)")]


def _setup_rules(claude_home: Path) -> list[StepResult]:
    """Prune dangling symlinks from ~/.claude/rules so orphans can't accumulate.

    The kernel lands verbatim in CLAUDE.md, so dotfiles writes no rule files of
    its own — but Claude Code *does* auto-load ~/.claude/rules/*.md, and a prior
    (bash-era) setup left symlinks into a since-deleted source tree. Those broken
    links read as a healthy surface in ``agent overview`` while contributing
    nothing. Self-heal every run: a non-resolving entry is dead weight, period.
    """
    rules_dir = claude_home / "rules"
    pruned = prune_broken_symlinks(rules_dir)
    if pruned == 0:
        return []
    return [StepResult(level="success", message=f"Pruned {pruned} orphaned rule links")]


def _setup_marketplaces(dotfiles_dir: Path, claude_home: Path) -> list[StepResult]:
    """Merge extraKnownMarketplaces from marketplaces.json → settings.json."""
    src = dotfiles_dir / "ai" / "agents" / "claude" / "marketplaces.json"
    if not src.is_file():
        return []
    marketplaces = load_json_or(src, {})
    settings = _load_settings(claude_home)
    updated = merge_replace(settings, ["extraKnownMarketplaces"], marketplaces)
    _save_settings(claude_home, updated)
    return [
        StepResult(level="success", message=f"Configured {len(marketplaces)} plugin marketplaces")
    ]


def parse_plugins_yaml(plugins_yaml: Path) -> _JsonDict:
    """Parse plugins.yaml and return {plugin_id: True, ...}.

    Bare names get ``@claude-plugins-official`` suffix; names containing ``@``
    are used as-is. Comment lines and blanks are skipped.
    """
    import yaml  # pyyaml — only imported here to keep top-level imports minimal

    try:
        raw: object = yaml.safe_load(plugins_yaml.read_text()) or []
    except (yaml.YAMLError, OSError):
        return {}

    result: _JsonDict = {}
    if not isinstance(raw, list):
        return {}
    for item in raw:  # type: ignore[union-attr]
        if not isinstance(item, str) or not item.strip() or item.strip().startswith("#"):
            continue
        plugin = item.strip()
        key = plugin if "@" in plugin else f"{plugin}@claude-plugins-official"
        result[key] = True
    return result


def _setup_plugins(dotfiles_dir: Path, claude_home: Path) -> list[StepResult]:
    """Replace enabledPlugins in settings.json from plugins.yaml."""
    src = dotfiles_dir / "ai" / "agents" / "claude" / "plugins.yaml"
    if not src.is_file():
        return []
    plugins = parse_plugins_yaml(src)
    settings = _load_settings(claude_home)
    updated = merge_replace(settings, ["enabledPlugins"], plugins)
    _save_settings(claude_home, updated)
    return [StepResult(level="success", message=f"Enabled {len(plugins)} Claude Code plugins")]


def _setup_permissions(dotfiles_dir: Path, claude_home: Path) -> list[StepResult]:
    """Replace permissions.{allow,deny,defaultMode} from permissions.json."""
    src = dotfiles_dir / "ai" / "agents" / "claude" / "permissions.json"
    if not src.is_file():
        return []
    perms_src = load_json_or(src, {})
    settings = _load_settings(claude_home)

    existing_perms = cast(_JsonDict, settings.get("permissions") or {})
    default_mode = perms_src.get("defaultMode") or existing_perms.get("defaultMode") or "auto"
    new_perms: _JsonDict = {
        **existing_perms,
        "allow": perms_src.get("allow", []),
        "deny": perms_src.get("deny", []),
        "defaultMode": default_mode,
    }
    updated = merge_replace(settings, ["permissions"], new_perms)
    _save_settings(claude_home, updated)

    a = len(cast("list[str]", perms_src.get("allow", [])))
    d = len(cast("list[str]", perms_src.get("deny", [])))
    return [
        StepResult(
            level="success", message=f"Permissions: {a} allow, {d} deny (~/.claude/settings.json)"
        )
    ]


def _setup_mcp(
    dotfiles_dir: Path, home: Path, claude_home: Path, *, reset_mcp: bool
) -> list[StepResult]:
    """Merge managed MCP servers into ~/.claude.json (.mcpServers)."""
    claude_json = home / ".claude.json"
    skip = mcp_skip(home)
    servers = mcp_servers_for(dotfiles_dir, "claude", skip=skip)

    existing = load_json_or(claude_json, {})
    existing_mcp = cast(_JsonDict, existing.get("mcpServers") or {})
    new_mcp = merge_managed_mcp(
        existing_mcp,
        servers,
        managed_keys=set(mcp_servers_for(dotfiles_dir, "claude").keys()),
        reset_mcp=reset_mcp,
    )
    updated = merge_replace(existing, ["mcpServers"], new_mcp)
    write_json_safely(claude_json, updated)
    return [
        StepResult(level="success", message=f"Configured {len(servers)} MCP servers (Claude Code)")
    ]


def _rewrite_http_to_mcp_remote(entry: _JsonDict) -> _JsonDict:
    """Rewrite a type=http MCP entry as npx -y mcp-remote <url> [--header=K:V ...]."""
    if entry.get("type") != "http" or not entry.get("url"):
        return entry
    url = cast(str, entry["url"])
    headers = cast(_JsonDict, entry.get("headers") or {})
    header_args = [f"--header={k}:{v}" for k, v in headers.items()]
    args: list[str] = ["-y", "mcp-remote", url, *header_args]
    return {"command": "npx", "args": args}


def _desktop_servers(
    dotfiles_dir: Path, home: Path, *, reset_mcp: bool
) -> tuple[_JsonDict, set[str]]:
    """Return (servers_dict, managed_keys) for Claude Desktop (claude + desktop targets)."""
    skip = mcp_skip(home)
    servers_claude = mcp_servers_for(dotfiles_dir, "claude", skip=skip)
    servers_desktop = mcp_servers_for(dotfiles_dir, "desktop", skip=skip)
    # desktop overrides claude for same-named entries
    raw: _JsonDict = {**servers_claude, **servers_desktop}

    managed_all = set(mcp_servers_for(dotfiles_dir, "claude").keys()) | set(
        mcp_servers_for(dotfiles_dir, "desktop").keys()
    )

    # Rewrite http type → mcp-remote; strip targets key
    servers: _JsonDict = {}
    for name, cfg in raw.items():
        cfg_dict = cast(_JsonDict, cfg)
        cleaned = {k: v for k, v in cfg_dict.items() if k != "targets"}
        servers[name] = _rewrite_http_to_mcp_remote(cleaned)

    return servers, managed_all


def _setup_desktop(dotfiles_dir: Path, home: Path, *, reset_mcp: bool) -> list[StepResult]:
    """Merge MCP servers + desktop-preferences into ~/Library/.../claude_desktop_config.json."""
    desktop_config = home / _DESKTOP_CONFIG_REL
    desktop_config.parent.mkdir(parents=True, exist_ok=True)

    results: list[StepResult] = []
    existing = load_json_or(desktop_config, {})

    mcp_json = dotfiles_dir / "ai" / "agents" / "shared" / "mcp-servers.json"
    if mcp_json.is_file():
        servers, managed_keys = _desktop_servers(dotfiles_dir, home, reset_mcp=reset_mcp)
        existing_mcp = cast(_JsonDict, existing.get("mcpServers") or {})
        new_mcp = merge_managed_mcp(
            existing_mcp, servers, managed_keys=managed_keys, reset_mcp=reset_mcp
        )
        existing = merge_replace(existing, ["mcpServers"], new_mcp)
        results.append(
            StepResult(
                level="success", message=f"Configured {len(servers)} MCP servers (Claude Desktop)"
            )
        )

    prefs_src = dotfiles_dir / "ai" / "agents" / "claude" / "desktop-preferences.json"
    if prefs_src.is_file():
        prefs_file = load_json_or(prefs_src, {})
        prefs = cast(_JsonDict, prefs_file.get("preferences") or {})
        existing_prefs = cast(_JsonDict, existing.get("preferences") or {})
        # dotfiles prefs are base; existing user prefs win on conflict
        merged_prefs: _JsonDict = {**prefs, **existing_prefs}
        existing = merge_replace(existing, ["preferences"], merged_prefs)
        results.append(
            StepResult(level="success", message=f"Configured {len(prefs)} Desktop preferences")
        )

    write_json_safely(desktop_config, existing)
    return results


def _setup_hooks(dotfiles_dir: Path, claude_home: Path) -> list[StepResult]:
    """Replace .hooks in settings.json from hooks.json."""
    src = dotfiles_dir / "ai" / "agents" / "claude" / "hooks.json"
    if not src.is_file():
        return []
    hooks_file = load_json_or(src, {})
    hooks: _JsonDict = cast(_JsonDict, hooks_file.get("hooks") or {})
    settings = _load_settings(claude_home)
    updated = merge_replace(settings, ["hooks"], hooks)
    _save_settings(claude_home, updated)
    n = len(hooks)
    return [StepResult(level="success", message=f"Configured {n} hook events")]


def _setup_statusline(dotfiles_dir: Path, claude_home: Path) -> list[StepResult]:
    """Set .statusLine to {type: command, command: <path to statusline.sh>}."""
    src = dotfiles_dir / "ai" / "agents" / "claude" / "statusline.sh"
    if not src.is_file():
        return []
    src.chmod(src.stat().st_mode | 0o111)  # chmod +x
    status_line: _JsonDict = {"type": "command", "command": str(src)}
    settings = _load_settings(claude_home)
    updated = merge_replace(settings, ["statusLine"], status_line)
    _save_settings(claude_home, updated)
    return [StepResult(level="success", message="Statusline configured")]


def _setup_preferences(claude_home: Path) -> list[StepResult]:
    """Set voiceEnabled, preferredNotifChannel, defaultMode in settings.json."""
    settings = _load_settings(claude_home)
    settings = merge_replace(settings, ["voiceEnabled"], True)
    settings = merge_replace(settings, ["preferredNotifChannel"], "terminal_bell")
    settings = merge_replace(settings, ["defaultMode"], "acceptEdits")
    _save_settings(claude_home, settings)
    return [StepResult(level="success", message="Voice mode + terminal bell + acceptEdits enabled")]


def _install_external_skills(
    runner: ProcessRunner,
    home: Path,
    lines: list[str],
) -> tuple[int, int]:
    """Install missing external skills; return (total_count, installed_count)."""
    entries = [s for s in (ln.strip() for ln in lines) if s and not s.startswith("#")]
    installed = sum(1 for e in entries if _install_external_one(runner, home, e))
    return len(entries), installed


def _install_external_one(runner: ProcessRunner, home: Path, entry: str) -> bool:
    """Install one external skill spec if absent; return True iff newly installed."""
    skill_name = entry.rsplit("@", 1)[-1] if "@" in entry else entry
    if _skill_present(home, skill_name):
        return False
    return runner.run(("npx", "skills", "add", entry, "-g", "-y"), check=False).exit_code == 0


def _setup_skills(
    runner: ProcessRunner,
    dotfiles_dir: Path,
    home: Path,
    *,
    which: Callable[[str], str | None],
) -> list[StepResult]:
    """deploy_skills(claude-code) + install external skills from external-skills.txt."""
    results: list[StepResult] = [deploy_skills(runner, dotfiles_dir, "claude-code", which=which)]

    ext_file = dotfiles_dir / "ai" / "agents" / "claude" / "external-skills.txt"
    if not ext_file.is_file() or which("npx") is None:
        return results

    ext_count, ext_installed = _install_external_skills(
        runner, home, ext_file.read_text().splitlines()
    )
    if ext_installed > 0:
        results.append(
            StepResult(level="success", message=f"Installed {ext_installed} external skills")
        )
    results.append(
        StepResult(
            level="success", message=f"{ext_count} external skills tracked (external-skills.txt)"
        )
    )
    return results


def _skill_present(home: Path, skill_name: str) -> bool:
    """Return True if skill_name directory exists in ~/.agents/skills/ or ~/.claude/skills/."""
    return (home / ".agents" / "skills" / skill_name).is_dir() or (
        home / ".claude" / "skills" / skill_name
    ).is_dir()


# ---------------------------------------------------------------------------
# Clean mode
# ---------------------------------------------------------------------------


def _setup_clean(dotfiles_dir: Path, home: Path, claude_home: Path) -> list[StepResult]:
    """Prune nonconforming plugins, marketplaces, stale mcp__ perms, stale projects."""
    results: list[StepResult] = []
    results.extend(_clean_plugins(dotfiles_dir, claude_home))
    results.extend(_clean_marketplaces(dotfiles_dir, claude_home))
    results.extend(_clean_mcp_permissions(dotfiles_dir, claude_home))
    results.extend(_clean_stale_projects(home))
    return results


def _expected_plugin_ids(dotfiles_dir: Path) -> set[str]:
    plugins_yaml = dotfiles_dir / "ai" / "agents" / "claude" / "plugins.yaml"
    if not plugins_yaml.is_file():
        return set()
    return set(parse_plugins_yaml(plugins_yaml).keys())


def _clean_plugins(dotfiles_dir: Path, claude_home: Path) -> list[StepResult]:
    settings = _load_settings(claude_home)
    current = cast(_JsonDict, settings.get("enabledPlugins") or {})
    expected = _expected_plugin_ids(dotfiles_dir)
    kept = {k: v for k, v in current.items() if k in expected}
    removed = len(current) - len(kept)
    updated = merge_replace(settings, ["enabledPlugins"], kept)
    _save_settings(claude_home, updated)
    return [StepResult(level="success", message=f"Removed {removed} nonconforming plugins")]


def _expected_marketplace_ids(dotfiles_dir: Path) -> set[str]:
    src = dotfiles_dir / "ai" / "agents" / "claude" / "marketplaces.json"
    return set(load_json_or(src, {}).keys())


def _clean_marketplaces(dotfiles_dir: Path, claude_home: Path) -> list[StepResult]:
    settings = _load_settings(claude_home)
    current = cast(_JsonDict, settings.get("extraKnownMarketplaces") or {})
    expected = _expected_marketplace_ids(dotfiles_dir)
    kept = {k: v for k, v in current.items() if k in expected}
    removed = len(current) - len(kept)
    updated = merge_replace(settings, ["extraKnownMarketplaces"], kept)
    _save_settings(claude_home, updated)
    return [StepResult(level="success", message=f"Removed {removed} nonconforming marketplaces")]


def _is_stale_mcp_perm(perm: str, expected_plugins: set[str], expected_mcp: set[str]) -> bool:
    """Return True if an mcp__ permission refers to a no-longer-configured server/plugin."""
    if perm.startswith("mcp__plugin_"):
        plugin_part = perm[len("mcp__plugin_") :]
        plugin_name = plugin_part.split("_", 1)[0].lower()
        return not any(ep.split("@")[0].lower() == plugin_name for ep in expected_plugins)
    if perm.startswith("mcp__"):
        # Permissions are mcp__<server>__<tool> or mcp__<server>; match on the
        # server prefix so a tool-scoped grant (mcp__context7__search) is kept
        # whenever its server is known.
        server_name = perm[len("mcp__") :].split("__", 1)[0]
        return server_name not in expected_mcp
    return False


def _clean_mcp_permissions(dotfiles_dir: Path, claude_home: Path) -> list[StepResult]:
    expected_plugins = _expected_plugin_ids(dotfiles_dir)
    # Every registry server (all targets), not just Claude's — a cursor-only
    # server's permission must not be pruned from Claude's allow-list. Matches
    # the original bash, which keyed on the whole mcp-servers.json.
    expected_mcp = all_mcp_server_names(dotfiles_dir)

    settings = _load_settings(claude_home)
    perms = cast(_JsonDict, settings.get("permissions") or {})
    allow = cast(list[str], perms.get("allow") or [])

    cleaned = [p for p in allow if not _is_stale_mcp_perm(p, expected_plugins, expected_mcp)]
    removed = len(allow) - len(cleaned)

    new_perms: _JsonDict = {**perms, "allow": cleaned}
    updated = merge_replace(settings, ["permissions"], new_perms)
    _save_settings(claude_home, updated)
    return [StepResult(level="success", message=f"Removed {removed} stale MCP permissions")]


def _clean_stale_projects(home: Path) -> list[StepResult]:
    claude_json = home / ".claude.json"
    if not claude_json.is_file():
        return []
    data = load_json_or(claude_json, {})
    projects = cast(_JsonDict, data.get("projects") or {})
    kept = {k: v for k, v in projects.items() if Path(k).is_dir()}
    removed = len(projects) - len(kept)
    updated = merge_replace(data, ["projects"], kept)
    write_json_safely(claude_json, updated)
    return [StepResult(level="success", message=f"Removed {removed} stale project entries")]
