#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=./print_utils.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/print_utils.sh"

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
TYPEWHISPER_CONFIG_DIR="$DOTFILES_DIR/macos/typewhisper"
TYPEWHISPER_SUPPORT_DIR="$HOME/Library/Application Support/TypeWhisper"
TYPEWHISPER_PREFS="$HOME/Library/Preferences/com.typewhisper.mac.plist"
TYPEWHISPER_APP="/Applications/TypeWhisper.app"

usage() {
    printf "Usage: dotfiles typewhisper <status|apply> [--quit] [--reopen]\n"
    printf "\n"
    printf "Commands:\n"
    printf "  status          Show installed app, running state, configured workflow summary\n"
    printf "  apply           Apply tracked preferences and workflow configuration\n"
    printf "\n"
    printf "Options for apply:\n"
    printf "  --quit          Quit TypeWhisper before applying live SQLite-backed settings\n"
    printf "  --reopen        Reopen TypeWhisper after applying\n"
}

is_typewhisper_running() {
    pgrep -x "TypeWhisper" >/dev/null 2>&1
}

quit_typewhisper() {
    if ! is_typewhisper_running; then
        return 0
    fi

    print_action "Quitting TypeWhisper"
    osascript -e 'tell application "TypeWhisper" to quit' >/dev/null 2>&1 || true
    for _ in {1..30}; do
        if ! is_typewhisper_running; then
            print_success "TypeWhisper stopped"
            return 0
        fi
        sleep 0.2
    done

    print_error "TypeWhisper is still running; quit it manually and retry"
    return 1
}

status_typewhisper() {
    print_header "TypeWhisper configuration"

    print_section "App"
    if [[ -d "$TYPEWHISPER_APP" ]]; then
        print_success "Installed at $TYPEWHISPER_APP"
    else
        print_error "TypeWhisper.app not installed"
    fi

    if is_typewhisper_running; then
        print_info "TypeWhisper is running"
    else
        print_info "TypeWhisper is not running"
    fi

    print_section "Tracked config"
    for file in settings.json workflows.json dictionary.json; do
        if [[ -f "$TYPEWHISPER_CONFIG_DIR/$file" ]]; then
            print_success "$TYPEWHISPER_CONFIG_DIR/$file"
        else
            print_error "Missing $TYPEWHISPER_CONFIG_DIR/$file"
        fi
    done

    print_section "Live state"
    python3 - "$TYPEWHISPER_PREFS" "$TYPEWHISPER_SUPPORT_DIR" <<'PY'
import json
import pathlib
import plistlib
import sqlite3
import sys

prefs_path = pathlib.Path(sys.argv[1])
support_dir = pathlib.Path(sys.argv[2])

if prefs_path.exists():
    with prefs_path.open("rb") as handle:
        prefs = plistlib.load(handle)
    print(f"  selectedEngine: {prefs.get('selectedEngine', '<unset>')}")
    print(f"  selectedModel: {prefs.get('plugin.com.typewhisper.parakeet.selectedModel', '<unset>')}")
    print(f"  fillerWordsEnabled: {prefs.get('plugin.com.typewhisper.filler-words.enabled', '<unset>')}")
else:
    print("  preferences: missing")

workflow_store = support_dir / "workflows.store"
if workflow_store.exists():
    con = sqlite3.connect(workflow_store)
    rows = con.execute(
        "select ZNAME, ZISENABLED, ZTEMPLATERAW, ZTRIGGERKINDRAW, ZBEHAVIORDATA "
        "from ZWORKFLOW order by ZSORTORDER, ZNAME"
    ).fetchall()
    con.close()
    if not rows:
        print("  workflows: none")
    for name, enabled, template, trigger, behavior_blob in rows:
        fine_tuning = ""
        if behavior_blob:
            try:
                fine_tuning = json.loads(behavior_blob.decode("utf-8")).get("fineTuning", "")
            except Exception:
                fine_tuning = "<unreadable>"
        print(f"  workflow: {name} enabled={bool(enabled)} template={template} trigger={trigger} fineTuningChars={len(fine_tuning)}")
else:
    print("  workflows.store: missing")

dictionary_store = support_dir / "dictionary.store"
if dictionary_store.exists():
    con = sqlite3.connect(dictionary_store)
    term_count = con.execute("select count(*) from ZDICTIONARYENTRY where ZENTRYTYPE='term'").fetchone()[0]
    correction_count = con.execute("select count(*) from ZDICTIONARYENTRY where ZENTRYTYPE='correction'").fetchone()[0]
    con.close()
    print(f"  dictionary: terms={term_count} corrections={correction_count}")
else:
    print("  dictionary.store: missing")
PY
}

apply_typewhisper() {
    local quit_first=false
    local reopen=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --quit) quit_first=true ;;
            --reopen) reopen=true ;;
            -h|--help) usage; return 0 ;;
            *) print_error "Unknown option: $1"; usage; return 1 ;;
        esac
        shift
    done

    print_header "Applying TypeWhisper configuration"

    if [[ ! -d "$TYPEWHISPER_APP" ]]; then
        print_error "TypeWhisper.app is not installed"
        return 1
    fi

    if is_typewhisper_running; then
        if [[ "$quit_first" == true ]]; then
            quit_typewhisper
        else
            print_error "TypeWhisper is running"
            print_info "Run: macos/typewhisper.sh apply --quit --reopen"
            return 1
        fi
    fi

    print_section "Preferences and workflows"
    python3 - "$TYPEWHISPER_CONFIG_DIR" "$TYPEWHISPER_PREFS" "$TYPEWHISPER_SUPPORT_DIR" <<'PY'
import json
import pathlib
import plistlib
import sqlite3
import sys
import time
import uuid

config_dir = pathlib.Path(sys.argv[1])
prefs_path = pathlib.Path(sys.argv[2])
support_dir = pathlib.Path(sys.argv[3])

settings = json.loads((config_dir / "settings.json").read_text())["preferences"]
workflows = json.loads((config_dir / "workflows.json").read_text())["workflows"]
dictionary = json.loads((config_dir / "dictionary.json").read_text())

prefs_path.parent.mkdir(parents=True, exist_ok=True)
if prefs_path.exists():
    with prefs_path.open("rb") as handle:
        prefs = plistlib.load(handle)
else:
    prefs = {}

for key, value in settings.items():
    if key in {"hybridHotkey", "hybridHotkeys"}:
        prefs[key] = json.dumps(value, separators=(",", ":")).encode("utf-8")
    else:
        prefs[key] = value

with prefs_path.open("wb") as handle:
    plistlib.dump(prefs, handle, sort_keys=True)

support_dir.mkdir(parents=True, exist_ok=True)
workflow_store = support_dir / "workflows.store"
if not workflow_store.exists():
    raise SystemExit(f"Missing workflow store: {workflow_store}. Open TypeWhisper once, then retry.")

mac_epoch_offset = 978307200
now = time.time() - mac_epoch_offset
con = sqlite3.connect(workflow_store)
try:
    con.execute("pragma journal_mode=WAL")
    z_ent_row = con.execute("select Z_ENT from Z_PRIMARYKEY where Z_NAME='Workflow'").fetchone()
    z_ent = int(z_ent_row[0]) if z_ent_row else 1

    for index, workflow in enumerate(workflows):
        name = workflow["name"]
        existing = con.execute("select Z_PK, Z_OPT, ZCREATEDAT from ZWORKFLOW where ZNAME=?", (name,)).fetchone()
        behavior = dict(workflow.get("behavior", {}))
        behavior = {key: value for key, value in behavior.items() if value is not None}
        output = dict(workflow.get("output", {}))
        output = {key: value for key, value in output.items() if value is not None}
        trigger = dict(workflow.get("trigger", {}))
        trigger = {key: value for key, value in trigger.items() if value is not None}
        trigger.setdefault("kind", "global")
        trigger.setdefault("appBundleIdentifiers", [])
        trigger.setdefault("websitePatterns", [])
        trigger.setdefault("hotkeys", [])
        trigger.setdefault("hotkeyBehavior", "startDictation")

        behavior_blob = json.dumps(behavior, separators=(",", ":")).encode("utf-8")
        output_blob = json.dumps(output, separators=(",", ":")).encode("utf-8")
        trigger_blob = json.dumps(trigger, separators=(",", ":")).encode("utf-8")
        app_identifier = ",".join(trigger.get("appBundleIdentifiers", []))
        website_pattern = ",".join(trigger.get("websitePatterns", []))
        enabled = 1 if workflow.get("enabled", True) else 0
        sort_order = int(workflow.get("sortOrder", index))
        template = workflow.get("template", "custom")
        trigger_kind = trigger.get("kind", "global")

        if existing:
            z_pk, z_opt, created_at = existing
            con.execute(
                """
                update ZWORKFLOW
                set Z_OPT=?, ZISENABLED=?, ZSORTORDER=?, ZUPDATEDAT=?, ZTEMPLATERAW=?,
                    ZTRIGGERAPPBUNDLEIDENTIFIER=?, ZTRIGGERKINDRAW=?, ZTRIGGERWEBSITEPATTERN=?,
                    ZBEHAVIORDATA=?, ZOUTPUTDATA=?, ZTRIGGERDATA=?, ZTRIGGERHOTKEYDATA=NULL
                where Z_PK=?
                """,
                (
                    int(z_opt) + 1,
                    enabled,
                    sort_order,
                    now,
                    template,
                    app_identifier,
                    trigger_kind,
                    website_pattern,
                    behavior_blob,
                    output_blob,
                    trigger_blob,
                    z_pk,
                ),
            )
        else:
            max_pk = con.execute("select coalesce(max(Z_PK), 0) from ZWORKFLOW").fetchone()[0]
            z_pk = int(max_pk) + 1
            con.execute(
                """
                insert into ZWORKFLOW (
                    Z_PK, Z_ENT, Z_OPT, ZISENABLED, ZSORTORDER, ZCREATEDAT, ZUPDATEDAT,
                    ZNAME, ZTEMPLATERAW, ZTRIGGERAPPBUNDLEIDENTIFIER, ZTRIGGERKINDRAW,
                    ZTRIGGERWEBSITEPATTERN, ZID, ZBEHAVIORDATA, ZOUTPUTDATA, ZTRIGGERDATA, ZTRIGGERHOTKEYDATA
                ) values (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    z_pk,
                    z_ent,
                    enabled,
                    sort_order,
                    now,
                    now,
                    name,
                    template,
                    app_identifier,
                    trigger_kind,
                    website_pattern,
                    uuid.uuid4().bytes,
                    behavior_blob,
                    output_blob,
                    trigger_blob,
                ),
            )
            con.execute("update Z_PRIMARYKEY set Z_MAX=max(Z_MAX, ?) where Z_NAME='Workflow'", (z_pk,))

    con.commit()
    con.execute("pragma wal_checkpoint(full)")
finally:
    con.close()

dictionary_store = support_dir / "dictionary.store"
if not dictionary_store.exists():
    raise SystemExit(f"Missing dictionary store: {dictionary_store}. Open TypeWhisper once, then retry.")

terms = dictionary.get("terms", [])
corrections = dictionary.get("corrections", [])
con = sqlite3.connect(dictionary_store)
try:
    con.execute("pragma journal_mode=WAL")
    z_ent_row = con.execute("select Z_ENT from Z_PRIMARYKEY where Z_NAME='DictionaryEntry'").fetchone()
    z_ent = int(z_ent_row[0]) if z_ent_row else 1

    def next_pk():
        return int(con.execute("select coalesce(max(Z_PK), 0) from ZDICTIONARYENTRY").fetchone()[0]) + 1

    def bump_primary_key(z_pk):
        con.execute("update Z_PRIMARYKEY set Z_MAX=max(Z_MAX, ?) where Z_NAME='DictionaryEntry'", (z_pk,))

    for term in terms:
        if isinstance(term, str):
            original = term.strip()
            case_sensitive = False
            enabled = True
        else:
            original = str(term.get("term", term.get("original", ""))).strip()
            case_sensitive = bool(term.get("caseSensitive", False))
            enabled = bool(term.get("enabled", True))
        if not original:
            continue
        existing = con.execute(
            "select Z_PK from ZDICTIONARYENTRY where ZENTRYTYPE='term' and lower(ZORIGINAL)=lower(?)",
            (original,),
        ).fetchone()
        if existing:
            con.execute(
                "update ZDICTIONARYENTRY set ZCASESENSITIVE=?, ZISENABLED=? where Z_PK=?",
                (1 if case_sensitive else 0, 1 if enabled else 0, existing[0]),
            )
        else:
            z_pk = next_pk()
            con.execute(
                """
                insert into ZDICTIONARYENTRY (
                    Z_PK, Z_ENT, Z_OPT, ZCASESENSITIVE, ZISENABLED, ZUSAGECOUNT,
                    ZCREATEDAT, ZENTRYTYPE, ZORIGINAL, ZREPLACEMENT, ZID
                ) values (?, ?, 1, ?, ?, 0, ?, 'term', ?, NULL, ?)
                """,
                (z_pk, z_ent, 1 if case_sensitive else 0, 1 if enabled else 0, now, original, uuid.uuid4().bytes),
            )
            bump_primary_key(z_pk)

    for correction in corrections:
        original = str(correction.get("original", "")).strip()
        replacement = str(correction.get("replacement", ""))
        case_sensitive = bool(correction.get("caseSensitive", False))
        enabled = bool(correction.get("enabled", True))
        if not original:
            continue
        existing = con.execute(
            "select Z_PK from ZDICTIONARYENTRY where ZENTRYTYPE='correction' and lower(ZORIGINAL)=lower(?)",
            (original,),
        ).fetchone()
        if existing:
            con.execute(
                "update ZDICTIONARYENTRY set ZCASESENSITIVE=?, ZISENABLED=?, ZREPLACEMENT=? where Z_PK=?",
                (1 if case_sensitive else 0, 1 if enabled else 0, replacement, existing[0]),
            )
        else:
            z_pk = next_pk()
            con.execute(
                """
                insert into ZDICTIONARYENTRY (
                    Z_PK, Z_ENT, Z_OPT, ZCASESENSITIVE, ZISENABLED, ZUSAGECOUNT,
                    ZCREATEDAT, ZENTRYTYPE, ZORIGINAL, ZREPLACEMENT, ZID
                ) values (?, ?, 1, ?, ?, 0, ?, 'correction', ?, ?, ?)
                """,
                (z_pk, z_ent, 1 if case_sensitive else 0, 1 if enabled else 0, now, original, replacement, uuid.uuid4().bytes),
            )
            bump_primary_key(z_pk)

    con.commit()
    con.execute("pragma wal_checkpoint(full)")
finally:
    con.close()

print(
    f"Applied {len(settings)} preferences, {len(workflows)} workflow(s), "
    f"{len(terms)} dictionary term(s), and {len(corrections)} correction(s)."
)
PY
    print_success "Applied tracked TypeWhisper config"

    if command -v killall >/dev/null 2>&1; then
        killall cfprefsd >/dev/null 2>&1 || true
    fi

    if [[ "$reopen" == true ]]; then
        print_action "Reopening TypeWhisper"
        open -a "TypeWhisper"
    fi

    print_completion "TypeWhisper configuration applied"
}

command="${1:-status}"
shift || true
case "$command" in
    status) status_typewhisper "$@" ;;
    apply) apply_typewhisper "$@" ;;
    -h|--help|help) usage ;;
    *) print_error "Unknown TypeWhisper command: $command"; usage; exit 1 ;;
esac
