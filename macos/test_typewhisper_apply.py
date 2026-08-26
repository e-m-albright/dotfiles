import sqlite3

from typewhisper_apply import upsert_dictionary, upsert_workflows

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
    con = _connect(WORKFLOW_SCHEMA)
    upsert_workflows(con, [{"name": "Clean", "enabled": False}], NOW)
    row = con.execute(
        "select Z_PK, Z_ENT, ZISENABLED, ZSORTORDER, ZNAME, ZTRIGGERKINDRAW from ZWORKFLOW"
    ).fetchone()
    assert row == (1, 2, 0, 0, "Clean", "global")
    assert con.execute("select Z_MAX from Z_PRIMARYKEY where Z_NAME='Workflow'").fetchone() == (1,)


def test_workflow_update_existing_bumps_opt_and_keeps_created_at() -> None:
    con = _connect(WORKFLOW_SCHEMA)
    upsert_workflows(con, [{"name": "Clean"}], NOW)
    upsert_workflows(con, [{"name": "Clean", "enabled": False, "sortOrder": 7}], NOW + 5)
    rows = con.execute(
        "select Z_OPT, ZISENABLED, ZSORTORDER, ZCREATEDAT, ZUPDATEDAT from ZWORKFLOW"
    ).fetchall()
    assert rows == [(2, 0, 7, NOW, NOW + 5)]


def test_term_insert_and_case_insensitive_update() -> None:
    con = _connect(DICTIONARY_SCHEMA)
    upsert_dictionary(con, ["Codex"], [], NOW)
    upsert_dictionary(con, [{"term": "codex", "caseSensitive": True, "enabled": False}], [], NOW)
    rows = con.execute(
        "select ZENTRYTYPE, ZORIGINAL, ZCASESENSITIVE, ZISENABLED, ZREPLACEMENT"
        " from ZDICTIONARYENTRY"
    ).fetchall()
    assert rows == [("term", "Codex", 1, 0, None)]


def test_correction_insert_then_update_replacement() -> None:
    con = _connect(DICTIONARY_SCHEMA)
    upsert_dictionary(con, [], [{"original": "teh", "replacement": "the"}], NOW)
    upsert_dictionary(con, [], [{"original": "Teh", "replacement": "THE", "enabled": False}], NOW)
    rows = con.execute(
        "select ZENTRYTYPE, ZORIGINAL, ZREPLACEMENT, ZISENABLED, Z_PK from ZDICTIONARYENTRY"
    ).fetchall()
    assert rows == [("correction", "teh", "THE", 0, 1)]
    assert con.execute(
        "select Z_MAX from Z_PRIMARYKEY where Z_NAME='DictionaryEntry'"
    ).fetchone() == (1,)


def test_terms_and_corrections_share_pk_sequence() -> None:
    con = _connect(DICTIONARY_SCHEMA)
    upsert_dictionary(con, ["Codex"], [{"original": "teh", "replacement": "the"}], NOW)
    assert con.execute("select max(Z_PK) from ZDICTIONARYENTRY").fetchone() == (2,)
    assert con.execute(
        "select Z_MAX from Z_PRIMARYKEY where Z_NAME='DictionaryEntry'"
    ).fetchone() == (2,)
