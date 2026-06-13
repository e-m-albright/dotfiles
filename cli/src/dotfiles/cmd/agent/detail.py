"""Cockpit drill-downs: subagents, hooks, and permissions in depth.

Each builder is a projection of the same sources the overview uses — the fleet
model, the VENDORS registry, and the live configs — so a drill-down can never
disagree with the dashboard it expands. No vendor lists, no probes of its own.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from dotfiles.agent import HOOK_INTENTS, VENDORS
from dotfiles.cmd.agent.config import SettingsWithPermissions, load_config
from dotfiles.cmd.agent.fleet import Fleet
from dotfiles.cmd.agent.skills import parse_frontmatter
from dotfiles.fsutil import list_dir, read_text_or

# ---------------------------------------------------------------------------
# Subagents — canonical set + per-vendor deployment, with descriptions
# ---------------------------------------------------------------------------


class SubagentDetail(BaseModel):
    """One canonical subagent: its description and where it's live."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    cells: dict[str, bool]  # vendor → deployed (vendors with a subagents deploy)


def subagent_details(*, dotfiles_dir: Path, home: Path) -> list[SubagentDetail]:
    """Every ai/subagents/*.md with its frontmatter description and deploy state."""
    root = dotfiles_dir / "ai" / "subagents"
    if not root.is_dir():
        return []
    deploy_dirs = {v.name: home / d.path for v in VENDORS if (d := v.deploy("subagents"))}
    details: list[SubagentDetail] = []
    for entry in sorted(list_dir(root), key=lambda p: p.name):
        if entry.is_dir() or entry.suffix != ".md":
            continue
        fields, _body = parse_frontmatter(read_text_or(entry))
        details.append(
            SubagentDetail(
                name=entry.stem,
                description=fields.get("description", "") or "(unreadable)",
                cells={
                    vendor: (dest / entry.name).exists() for vendor, dest in deploy_dirs.items()
                },
            )
        )
    return details


# ---------------------------------------------------------------------------
# Hooks — live wiring per vendor, intent by intent
# ---------------------------------------------------------------------------


class HookWiring(BaseModel):
    """One vendor's live hook state: where it's wired and which intents are in."""

    model_config = ConfigDict(frozen=True)

    vendor: str
    stance: str  # deploy / local / none (native doesn't occur for hooks)
    path: str = ""  # the live config (or extension file) probed
    wired: tuple[str, ...] = ()  # intents proven in the live config
    note: str = ""  # Local reason, or "extension" for a non-intent deploy


def _wired_intents(path: Path) -> tuple[str, ...]:
    try:
        text = path.read_text()
    except OSError:
        return ()
    return tuple(intent for intent, script in HOOK_INTENTS if script in text)


def hook_wirings(fleet: Fleet, *, home: Path) -> list[HookWiring]:
    """Per-vendor live hook wiring — the drill-down behind the Hooks matrix."""
    wirings: list[HookWiring] = []
    for vendor in VENDORS:
        cell = fleet.cell(vendor.name, "hooks")
        deploy = vendor.deploy("hooks")
        if deploy is None:
            wirings.append(HookWiring(vendor=vendor.name, stance=cell.stance, note=cell.note))
        elif deploy.proof == "hook-intents":
            path = home / deploy.path
            wirings.append(
                HookWiring(
                    vendor=vendor.name,
                    stance="deploy",
                    path=str(path),
                    wired=_wired_intents(path),
                )
            )
        else:  # a hook deploy that isn't the shared-intent wiring (pi's extension)
            wirings.append(
                HookWiring(
                    vendor=vendor.name,
                    stance="deploy",
                    path=str(home / deploy.path),
                    note="extension",
                )
            )
    return wirings


# ---------------------------------------------------------------------------
# Permissions — the deny floor, spelled out
# ---------------------------------------------------------------------------


class DenyList(BaseModel):
    """One permission source's deny entries — the safety floor, verbatim."""

    model_config = ConfigDict(frozen=True)

    label: str
    path: str
    entries: tuple[str, ...]


def deny_list(label: str, path: Path) -> DenyList | None:
    """The deny entries of a settings-shaped config, or None when absent."""
    cfg = load_config(path, SettingsWithPermissions)
    if cfg is None:
        return None
    entries = tuple(str(e) for e in cfg.permissions.deny)
    return DenyList(label=label, path=str(path), entries=entries)


# ---------------------------------------------------------------------------
# K1 liveness — the verify-before-done gate the uniform hook matrix can't see
# ---------------------------------------------------------------------------

K1_SCRIPT = "verify-before-done.sh"
K1_EVENTS: tuple[str, ...] = ("Stop", "SubagentStop")


class _HookCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")
    command: str = ""


class _HookEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    hooks: list[_HookCommand] = []


class _SettingsHooks(BaseModel):
    """Just the hooks map of a Claude settings.json (event name → entries)."""

    model_config = ConfigDict(extra="ignore")
    hooks: dict[str, list[_HookEntry]] = {}


class K1Liveness(BaseModel):
    """Whether the verify-before-done (K1) gate is wired in the DEPLOYED Claude
    settings, per event.

    K1 sits outside the uniform HOOK_INTENTS the cockpit matrix checks, so without
    this probe a silently dropped gate — a Claude update rewriting settings.json, a
    partial setup — would read as all-green while the most safety-critical hook is
    dead. The check is structural (the script must be a real ``command`` value in
    the event's entries, not just a substring somewhere in the file)."""

    model_config = ConfigDict(frozen=True)

    settings_path: str
    events: dict[str, bool]  # event name → the K1 script wired there

    @property
    def live(self) -> bool:
        return bool(self.events) and all(self.events.values())


def k1_events_in(settings_path: Path) -> dict[str, bool]:
    """Per-event: is the K1 script a real ``command`` value in that event's entries?

    Structural (parsed, not grepped) and path-agnostic, so the runtime probe (the
    deployed ~/.claude/settings.json) and the source-of-truth gate (the repo's
    ai/agents/claude/hooks.json) verify the K1 wiring the exact same way."""
    cfg = load_config(settings_path, _SettingsHooks)
    hooks = cfg.hooks if cfg is not None else {}
    return {
        event: any(K1_SCRIPT in h.command for entry in hooks.get(event, []) for h in entry.hooks)
        for event in K1_EVENTS
    }


def k1_liveness(home: Path) -> K1Liveness:
    """Structurally probe ~/.claude/settings.json for the K1 verify hook in each of
    Stop and SubagentStop — parsed, not grepped."""
    settings = home / ".claude" / "settings.json"
    return K1Liveness(settings_path=str(settings), events=k1_events_in(settings))
