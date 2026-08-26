import json
import plistlib
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from typewhisper_apply import apply_configuration, upsert_dictionary, upsert_workflows

NOW = 700000000.0

WORKFLOW_SCHEMA = """
create table Z_PRIMARYKEY (Z_ENT integer, Z_NAME text, Z_MAX integer);
insert into Z_PRIMARYKEY values (2, 'Workflow', 0);
create table ZWORKFLOW (
    Z_PK integer primary key, Z_ENT integer, Z_OPT integer,
    ZISENABLED integer, ZSORTORDER integer, ZCREATEDAT real, ZUPDATEDAT real,
    ZNAME text, ZTEMPLATERAW text, ZTRIGGERAPPBUNDLEIDENTIFIER text,
    ZTRIGGERKINDRAW text, ZTRIGGERWEBSITEPATTERN text, ZID blob,
    ZBEHAVIORDATA blob, ZOUTPUTDATA blob, ZTRIGGERDATA blob, ZTRIGGERHOTKEYDATA blob
);
"""

DICTIONARY_SCHEMA = """
create table Z_PRIMARYKEY (Z_ENT integer, Z_NAME text, Z_MAX integer);
insert into Z_PRIMARYKEY values (3, 'DictionaryEntry', 0);
create table ZDICTIONARYENTRY (
    Z_PK integer primary key, Z_ENT integer, Z_OPT integer,
    ZCASESENSITIVE integer, ZISENABLED integer, ZUSAGECOUNT integer,
    ZCREATEDAT real, ZENTRYTYPE text, ZORIGINAL text, ZREPLACEMENT text, ZID blob
);
"""


def _connect(schema: str) -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.executescript(schema)
    return con


def test_workflow_insert_new() -> None:
    with closing(_connect(WORKFLOW_SCHEMA)) as con:
        upsert_workflows(con, [{"name": "Clean", "enabled": False}], NOW)
        row = con.execute(
            "select Z_PK, Z_ENT, ZISENABLED, ZSORTORDER, ZNAME, ZTRIGGERKINDRAW from ZWORKFLOW"
        ).fetchone()
        assert row == (1, 2, 0, 0, "Clean", "global")
        assert con.execute("select Z_MAX from Z_PRIMARYKEY where Z_NAME='Workflow'").fetchone() == (
            1,
        )


def test_workflow_update_existing_bumps_opt_and_keeps_created_at() -> None:
    with closing(_connect(WORKFLOW_SCHEMA)) as con:
        upsert_workflows(con, [{"name": "Clean"}], NOW)
        upsert_workflows(con, [{"name": "Clean", "enabled": False, "sortOrder": 7}], NOW + 5)
        rows = con.execute(
            "select Z_OPT, ZISENABLED, ZSORTORDER, ZCREATEDAT, ZUPDATEDAT from ZWORKFLOW"
        ).fetchall()
        assert rows == [(2, 0, 7, NOW, NOW + 5)]


def test_term_insert_and_case_insensitive_update() -> None:
    with closing(_connect(DICTIONARY_SCHEMA)) as con:
        upsert_dictionary(con, ["Codex"], [], NOW)
        upsert_dictionary(
            con, [{"term": "codex", "caseSensitive": True, "enabled": False}], [], NOW
        )
        rows = con.execute(
            "select ZENTRYTYPE, ZORIGINAL, ZCASESENSITIVE, ZISENABLED, ZREPLACEMENT"
            " from ZDICTIONARYENTRY"
        ).fetchall()
        assert rows == [("term", "Codex", 1, 0, None)]


def test_correction_insert_then_update_replacement() -> None:
    with closing(_connect(DICTIONARY_SCHEMA)) as con:
        upsert_dictionary(con, [], [{"original": "teh", "replacement": "the"}], NOW)
        upsert_dictionary(
            con, [], [{"original": "Teh", "replacement": "THE", "enabled": False}], NOW
        )
        rows = con.execute(
            "select ZENTRYTYPE, ZORIGINAL, ZREPLACEMENT, ZISENABLED, Z_PK from ZDICTIONARYENTRY"
        ).fetchall()
        assert rows == [("correction", "teh", "THE", 0, 1)]
        assert con.execute(
            "select Z_MAX from Z_PRIMARYKEY where Z_NAME='DictionaryEntry'"
        ).fetchone() == (1,)


def test_terms_and_corrections_share_pk_sequence() -> None:
    with closing(_connect(DICTIONARY_SCHEMA)) as con:
        upsert_dictionary(con, ["Codex"], [{"original": "teh", "replacement": "the"}], NOW)
        assert con.execute("select max(Z_PK) from ZDICTIONARYENTRY").fetchone() == (2,)
        assert con.execute(
            "select Z_MAX from Z_PRIMARYKEY where Z_NAME='DictionaryEntry'"
        ).fetchone() == (2,)


def _write_config(config_dir: Path) -> None:
    config_dir.mkdir()
    (config_dir / "settings.json").write_text(json.dumps({"preferences": {"sound": True}}))
    (config_dir / "workflows.json").write_text(json.dumps({"workflows": [{"name": "Clean"}]}))
    (config_dir / "dictionary.json").write_text(json.dumps({"terms": ["Codex"]}))


def _write_store(path: Path, schema: str) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(schema)
        connection.commit()
    finally:
        connection.close()


def test_apply_configuration_preflights_both_stores_before_preferences(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    support_dir = tmp_path / "support"
    support_dir.mkdir()
    prefs = tmp_path / "prefs.plist"
    prefs.write_bytes(plistlib.dumps({"sound": False}))
    _write_config(config_dir)
    _write_store(support_dir / "workflows.store", WORKFLOW_SCHEMA)

    with pytest.raises(SystemExit, match="Missing dictionary store"):
        apply_configuration(config_dir, prefs, support_dir)

    assert plistlib.loads(prefs.read_bytes()) == {"sound": False}
    with closing(sqlite3.connect(support_dir / "workflows.store")) as connection:
        assert connection.execute("select count(*) from ZWORKFLOW").fetchone() == (0,)


def test_apply_configuration_restores_all_surfaces_after_late_failure(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    support_dir = tmp_path / "support"
    support_dir.mkdir()
    prefs = tmp_path / "prefs.plist"
    prefs.write_bytes(plistlib.dumps({"sound": False}))
    _write_config(config_dir)
    _write_store(support_dir / "workflows.store", WORKFLOW_SCHEMA)
    # A valid SQLite store that lacks TypeWhisper's dictionary schema fails only
    # after preferences and workflows have been written.
    _write_store(support_dir / "dictionary.store", "create table unrelated (id integer);")

    with pytest.raises(sqlite3.OperationalError, match="Z_PRIMARYKEY"):
        apply_configuration(config_dir, prefs, support_dir)

    assert plistlib.loads(prefs.read_bytes()) == {"sound": False}
    with closing(sqlite3.connect(support_dir / "workflows.store")) as connection:
        assert connection.execute("select count(*) from ZWORKFLOW").fetchone() == (0,)
