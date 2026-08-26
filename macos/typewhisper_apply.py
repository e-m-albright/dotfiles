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

    with prefs_path.open("wb") as handle:
        plistlib.dump(prefs, handle, sort_keys=True)


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


def main(argv: list[str]) -> None:
    config_dir = pathlib.Path(argv[1])
    prefs_path = pathlib.Path(argv[2])
    support_dir = pathlib.Path(argv[3])

    settings = json.loads((config_dir / "settings.json").read_text())["preferences"]
    workflows = json.loads((config_dir / "workflows.json").read_text())["workflows"]
    dictionary = json.loads((config_dir / "dictionary.json").read_text())

    apply_preferences(prefs_path, settings)

    support_dir.mkdir(parents=True, exist_ok=True)
    workflow_store = support_dir / "workflows.store"
    if not workflow_store.exists():
        raise SystemExit(
            f"Missing workflow store: {workflow_store}. Open TypeWhisper once, then retry."
        )

    now = time.time() - MAC_EPOCH_OFFSET
    _apply_store(workflow_store, lambda con: upsert_workflows(con, workflows, now))

    dictionary_store = support_dir / "dictionary.store"
    if not dictionary_store.exists():
        raise SystemExit(
            f"Missing dictionary store: {dictionary_store}. Open TypeWhisper once, then retry."
        )

    terms = dictionary.get("terms", [])
    corrections = dictionary.get("corrections", [])
    _apply_store(dictionary_store, lambda con: upsert_dictionary(con, terms, corrections, now))

    print(
        f"Applied {len(settings)} preferences, {len(workflows)} workflow(s), "
        f"{len(terms)} dictionary term(s), and {len(corrections)} correction(s)."
    )


if __name__ == "__main__":
    main(sys.argv)
