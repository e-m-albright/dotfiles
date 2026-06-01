"""Tests for LlmSettings and BenchResult model."""

import pytest

from dotfiles.core.models import BenchResult
from dotfiles.core.settings import LlmSettings

# ---------------------------------------------------------------------------
# LlmSettings — defaults and env reading
# ---------------------------------------------------------------------------


def test_llm_settings_defaults() -> None:
    s = LlmSettings()
    assert s.lms_host == "http://localhost:1234"
    assert s.pp_tokens == 128
    assert s.tg_tokens == 256
    assert s.load_ctx == 32768


def test_llm_settings_reads_lms_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LMS_HOST", "http://192.168.1.5:1234")
    s = LlmSettings()
    assert s.lms_host == "http://192.168.1.5:1234"


def test_llm_settings_reads_pp_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PP_TOKENS", "64")
    s = LlmSettings()
    assert s.pp_tokens == 64


def test_llm_settings_reads_tg_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TG_TOKENS", "512")
    s = LlmSettings()
    assert s.tg_tokens == 512


def test_llm_settings_reads_load_ctx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOAD_CTX", "65536")
    s = LlmSettings()
    assert s.load_ctx == 65536


# ---------------------------------------------------------------------------
# BenchResult — fields and tier property
# ---------------------------------------------------------------------------


def _make_result(tg_tps: float) -> BenchResult:
    return BenchResult(
        model="test-model",
        tg_tps=tg_tps,
        pp_tps=200.0,
        pp_tokens=128,
        pp_wall=0.64,
        ttft=0.05,
        reasoning_tokens=0,
        content_len=512,
    )


def test_bench_result_tier_autocomplete() -> None:
    assert _make_result(100.0).tier == "autocomplete-grade"


def test_bench_result_tier_autocomplete_above_100() -> None:
    assert _make_result(150.0).tier == "autocomplete-grade"


def test_bench_result_tier_interactive() -> None:
    assert _make_result(40.0).tier == "interactive-grade"


def test_bench_result_tier_interactive_mid() -> None:
    assert _make_result(60.0).tier == "interactive-grade"


def test_bench_result_tier_tolerable() -> None:
    assert _make_result(20.0).tier == "tolerable"


def test_bench_result_tier_tolerable_mid() -> None:
    assert _make_result(35.0).tier == "tolerable"


def test_bench_result_tier_painful() -> None:
    assert _make_result(19.9).tier == "painful"


def test_bench_result_tier_painful_zero() -> None:
    assert _make_result(0.0).tier == "painful"


def test_bench_result_reasoning_tokens_stored() -> None:
    r = BenchResult(
        model="thinking-model",
        tg_tps=55.0,
        pp_tps=180.0,
        pp_tokens=128,
        pp_wall=0.71,
        ttft=0.12,
        reasoning_tokens=512,
        content_len=200,
    )
    assert r.reasoning_tokens == 512
