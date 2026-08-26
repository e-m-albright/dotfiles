"""Apply tracked TypeWhisper preferences, workflows, and dictionary entries.

Runs under the system python3 with stdlib only. TypeWhisper stores dates and
IDs in Apple's Core Data schema: seconds since 2001, plus Z_PK/Z_ENT/Z_OPT
bookkeeping mirrored in Z_PRIMARYKEY.
"""

import json
import pathlib
import plistlib
import sqlite3
import sys
import time
import uuid
from tempfile import TemporaryDirectory
from typing import Any

from typewhisper_config import normalize_correction, normalize_term, normalize_workflow

MAC_EPOCH_OFFSET = 978307200


def apply_preferences(prefs_path: pathlib.Path, settings: dict[str, Any]) -> None:
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

    temporary = prefs_path.with_name(f".{prefs_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("wb") as handle:
            plistlib.dump(prefs, handle, sort_keys=True)
        temporary.replace(prefs_path)
    finally:
        temporary.unlink(missing_ok=True)


def upsert_workflows(con: sqlite3.Connection, workflows: list[dict[str, Any]], now: float) -> None:
    z_ent_row = con.execute("select Z_ENT from Z_PRIMARYKEY where Z_NAME='Workflow'").fetchone()
    z_ent = int(z_ent_row[0]) if z_ent_row else 1

    for index, workflow in enumerate(workflows):
        spec = normalize_workflow(workflow, index)
        name = spec.name
        existing = con.execute(
            "select Z_PK, Z_OPT, ZCREATEDAT from ZWORKFLOW where ZNAME=?", (name,)
        ).fetchone()
        behavior_blob = json.dumps(spec.behavior, separators=(",", ":")).encode("utf-8")
        output_blob = json.dumps(spec.output, separators=(",", ":")).encode("utf-8")
        trigger_blob = json.dumps(spec.trigger, separators=(",", ":")).encode("utf-8")
        enabled = 1 if spec.enabled else 0

        if existing:
            z_pk, z_opt, _created_at = existing
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
                    spec.sort_order,
                    now,
                    spec.template,
                    spec.app_identifier,
                    spec.trigger_kind,
                    spec.website_pattern,
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
                    ZTRIGGERWEBSITEPATTERN, ZID, ZBEHAVIORDATA, ZOUTPUTDATA, ZTRIGGERDATA,
                    ZTRIGGERHOTKEYDATA
                ) values (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    z_pk,
                    z_ent,
                    enabled,
                    spec.sort_order,
                    now,
                    now,
                    name,
                    spec.template,
                    spec.app_identifier,
                    spec.trigger_kind,
                    spec.website_pattern,
                    uuid.uuid4().bytes,
                    behavior_blob,
                    output_blob,
                    trigger_blob,
                ),
            )
            con.execute(
                "update Z_PRIMARYKEY set Z_MAX=max(Z_MAX, ?) where Z_NAME='Workflow'",
                (z_pk,),
            )


def upsert_dictionary(
    con: sqlite3.Connection,
    terms: list[Any],
    corrections: list[dict[str, Any]],
    now: float,
) -> None:
    z_ent_row = con.execute(
        "select Z_ENT from Z_PRIMARYKEY where Z_NAME='DictionaryEntry'"
    ).fetchone()
    z_ent = int(z_ent_row[0]) if z_ent_row else 1

    def next_pk() -> int:
        return (
            int(con.execute("select coalesce(max(Z_PK), 0) from ZDICTIONARYENTRY").fetchone()[0])
            + 1
        )

    def bump_primary_key(z_pk: int) -> None:
        con.execute(
            "update Z_PRIMARYKEY set Z_MAX=max(Z_MAX, ?) where Z_NAME='DictionaryEntry'",
            (z_pk,),
        )

    for term in terms:
        spec = normalize_term(term)
        if spec is None:
            continue
        existing = con.execute(
            "select Z_PK from ZDICTIONARYENTRY"
            " where ZENTRYTYPE='term' and lower(ZORIGINAL)=lower(?)",
            (spec.original,),
        ).fetchone()
        if existing:
            con.execute(
                "update ZDICTIONARYENTRY set ZCASESENSITIVE=?, ZISENABLED=? where Z_PK=?",
                (
                    1 if spec.case_sensitive else 0,
                    1 if spec.enabled else 0,
                    existing[0],
                ),
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
                (
                    z_pk,
                    z_ent,
                    1 if spec.case_sensitive else 0,
                    1 if spec.enabled else 0,
                    now,
                    spec.original,
                    uuid.uuid4().bytes,
                ),
            )
            bump_primary_key(z_pk)

    for correction in corrections:
        spec = normalize_correction(correction)
        if spec is None:
            continue
        existing = con.execute(
            "select Z_PK from ZDICTIONARYENTRY"
            " where ZENTRYTYPE='correction' and lower(ZORIGINAL)=lower(?)",
            (spec.original,),
        ).fetchone()
        if existing:
            con.execute(
                "update ZDICTIONARYENTRY"
                " set ZCASESENSITIVE=?, ZISENABLED=?, ZREPLACEMENT=? where Z_PK=?",
                (
                    1 if spec.case_sensitive else 0,
                    1 if spec.enabled else 0,
                    spec.replacement,
                    existing[0],
                ),
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
                (
                    z_pk,
                    z_ent,
                    1 if spec.case_sensitive else 0,
                    1 if spec.enabled else 0,
                    now,
                    spec.original,
                    spec.replacement,
                    uuid.uuid4().bytes,
                ),
            )
            bump_primary_key(z_pk)


def _apply_store(store: pathlib.Path, apply: Any) -> None:
    con = sqlite3.connect(store)
    try:
        con.execute("pragma journal_mode=WAL")
        apply(con)
        con.commit()
        con.execute("pragma wal_checkpoint(full)")
    finally:
        con.close()


def _copy_store(source: pathlib.Path, destination: pathlib.Path) -> None:
    source_connection = sqlite3.connect(source)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()


def _restore_preferences(path: pathlib.Path, original: bytes | None) -> None:
    if original is None:
        path.unlink(missing_ok=True)
        return
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.restore")
    try:
        temporary.write_bytes(original)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def apply_configuration(
    config_dir: pathlib.Path, prefs_path: pathlib.Path, support_dir: pathlib.Path
) -> tuple[int, int, int, int]:
    """Apply all three stores as one recoverable operation.

    SQLite cannot atomically commit independent WAL databases plus a plist. We
    therefore preflight every input and store, take consistent SQLite backups,
    and restore every surface if any later write fails.
    """
    settings = json.loads((config_dir / "settings.json").read_text())["preferences"]
    workflows = json.loads((config_dir / "workflows.json").read_text())["workflows"]
    dictionary = json.loads((config_dir / "dictionary.json").read_text())
    terms = dictionary.get("terms", [])
    corrections = dictionary.get("corrections", [])

    # Validate all tracked records before touching live state.
    for index, workflow in enumerate(workflows):
        normalize_workflow(workflow, index)
    for term in terms:
        normalize_term(term)
    for correction in corrections:
        normalize_correction(correction)

    workflow_store = support_dir / "workflows.store"
    dictionary_store = support_dir / "dictionary.store"
    for label, store in (("workflow", workflow_store), ("dictionary", dictionary_store)):
        if not store.exists():
            raise SystemExit(f"Missing {label} store: {store}. Open TypeWhisper once, then retry.")

    prefs_original = prefs_path.read_bytes() if prefs_path.exists() else None
    with TemporaryDirectory(prefix="dotfiles-typewhisper-backup-") as backup_dir:
        workflow_backup = pathlib.Path(backup_dir) / "workflows.store"
        dictionary_backup = pathlib.Path(backup_dir) / "dictionary.store"
        _copy_store(workflow_store, workflow_backup)
        _copy_store(dictionary_store, dictionary_backup)

        now = time.time() - MAC_EPOCH_OFFSET
        try:
            apply_preferences(prefs_path, settings)
            _apply_store(workflow_store, lambda con: upsert_workflows(con, workflows, now))
            _apply_store(
                dictionary_store,
                lambda con: upsert_dictionary(con, terms, corrections, now),
            )
        except BaseException:
            _restore_preferences(prefs_path, prefs_original)
            _copy_store(workflow_backup, workflow_store)
            _copy_store(dictionary_backup, dictionary_store)
            raise

    return len(settings), len(workflows), len(terms), len(corrections)


def main(argv: list[str]) -> None:
    counts = apply_configuration(
        pathlib.Path(argv[1]), pathlib.Path(argv[2]), pathlib.Path(argv[3])
    )
    settings_count, workflow_count, term_count, correction_count = counts
    print(
        f"Applied {settings_count} preferences, {workflow_count} workflow(s), "
        f"{term_count} dictionary term(s), and {correction_count} correction(s)."
    )


if __name__ == "__main__":
    main(sys.argv)
