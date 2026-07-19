"""Pure normalization for TypeWhisper's tracked JSON configuration."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkflowSpec:
    name: str
    behavior: dict[str, Any]
    output: dict[str, Any]
    trigger: dict[str, Any]
    app_identifier: str
    website_pattern: str
    enabled: bool
    sort_order: int
    template: str
    trigger_kind: str


@dataclass(frozen=True)
class DictionarySpec:
    original: str
    replacement: str | None
    case_sensitive: bool
    enabled: bool


def _without_none(value: object) -> dict[str, Any]:
    return {key: item for key, item in dict(value or {}).items() if item is not None}


def normalize_workflow(workflow: dict[str, Any], index: int) -> WorkflowSpec:
    trigger = _without_none(workflow.get("trigger"))
    trigger.setdefault("kind", "global")
    trigger.setdefault("appBundleIdentifiers", [])
    trigger.setdefault("websitePatterns", [])
    trigger.setdefault("hotkeys", [])
    trigger.setdefault("hotkeyBehavior", "startDictation")
    return WorkflowSpec(
        name=workflow["name"],
        behavior=_without_none(workflow.get("behavior")),
        output=_without_none(workflow.get("output")),
        trigger=trigger,
        app_identifier=",".join(trigger["appBundleIdentifiers"]),
        website_pattern=",".join(trigger["websitePatterns"]),
        enabled=bool(workflow.get("enabled", True)),
        sort_order=int(workflow.get("sortOrder", index)),
        template=str(workflow.get("template", "custom")),
        trigger_kind=str(trigger["kind"]),
    )


def normalize_term(term: str | dict[str, Any]) -> DictionarySpec | None:
    if isinstance(term, str):
        original = term.strip()
        case_sensitive = False
        enabled = True
    else:
        original = str(term.get("term", term.get("original", ""))).strip()
        case_sensitive = bool(term.get("caseSensitive", False))
        enabled = bool(term.get("enabled", True))
    if not original:
        return None
    return DictionarySpec(original, None, case_sensitive, enabled)


def normalize_correction(correction: dict[str, Any]) -> DictionarySpec | None:
    original = str(correction.get("original", "")).strip()
    if not original:
        return None
    return DictionarySpec(
        original=original,
        replacement=str(correction.get("replacement", "")),
        case_sensitive=bool(correction.get("caseSensitive", False)),
        enabled=bool(correction.get("enabled", True)),
    )
