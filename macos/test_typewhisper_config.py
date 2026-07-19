from typewhisper_config import normalize_correction, normalize_term, normalize_workflow


def test_normalize_workflow_defaults_and_drops_none() -> None:
    spec = normalize_workflow(
        {"name": "Clean", "behavior": {"tone": None}, "trigger": {"kind": None}}, 3
    )
    assert spec.behavior == {}
    assert spec.trigger["kind"] == "global"
    assert spec.sort_order == 3


def test_normalize_dictionary_entries() -> None:
    assert normalize_term("  Codex ").original == "Codex"
    assert normalize_term("  ") is None
    correction = normalize_correction({"original": "teh", "replacement": "the"})
    assert correction is not None
    assert correction.replacement == "the"
