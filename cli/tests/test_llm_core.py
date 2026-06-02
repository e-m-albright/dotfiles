"""Tests for LMStudioService — all network/subprocess calls injected via fakes."""

import pytest

from dotfiles.cmd.benchmark.service import (
    BENCH_PROMPT,
    LMStudioService,
    _is_estimate_line,
    _random_words,
)
from dotfiles.settings import LlmSettings
from dotfiles.testing.fakes import FakeHttpClient, FakeMultiPostHttpClient, FakeProcessRunner
from dotfiles.testing.llm_payloads import models_payload as _models_payload
from dotfiles.testing.llm_payloads import pp_payload as _pp_payload
from dotfiles.testing.llm_payloads import tg_payload as _tg_payload

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

COMPLETIONS_URL = "http://localhost:1234/api/v0/chat/completions"
MODELS_URL = "http://localhost:1234/api/v0/models"


def _settings(**overrides: object) -> LlmSettings:
    kwargs = {
        "lms_host": "http://localhost:1234",
        "pp_tokens": 128,
        "tg_tokens": 256,
        "load_ctx": 32768,
    }
    kwargs.update(overrides)
    return LlmSettings.model_validate(kwargs)


def _service(
    runner: FakeProcessRunner | None = None,
    http: FakeHttpClient | None = None,
    settings: LlmSettings | None = None,
    *,
    lms_on_path: bool = True,
) -> tuple[LMStudioService, FakeProcessRunner, FakeHttpClient]:
    r = runner or FakeProcessRunner()
    h = http or FakeHttpClient()
    s = settings or _settings()
    which_fn = (lambda _cmd: "/usr/local/bin/lms") if lms_on_path else (lambda _cmd: None)
    svc = LMStudioService(runner=r, http=h, settings=s, which=which_fn)
    return svc, r, h


# ---------------------------------------------------------------------------
# list_loaded
# ---------------------------------------------------------------------------


def test_list_loaded_returns_runner_stdout() -> None:
    svc, runner, _ = _service()
    runner.script(("lms", "ps"), stdout="model-a  loaded\n")
    assert svc.list_loaded() == "model-a  loaded\n"


def test_list_loaded_raises_when_lms_missing() -> None:
    svc, _, _ = _service(lms_on_path=False)
    with pytest.raises(RuntimeError, match="lms CLI not found"):
        svc.list_loaded()


# ---------------------------------------------------------------------------
# current_loaded_id
# ---------------------------------------------------------------------------


def test_current_loaded_id_returns_first_loaded() -> None:
    svc, _, http = _service()
    http.script_get(MODELS_URL, _models_payload("llama-3.2-1b"))
    assert svc.current_loaded_id() == "llama-3.2-1b"


def test_current_loaded_id_returns_none_when_none_loaded() -> None:
    svc, _, http = _service()
    http.script_get(MODELS_URL, {"data": [{"id": "llama", "state": "not-loaded"}]})
    assert svc.current_loaded_id() is None


def test_current_loaded_id_returns_none_on_empty_data() -> None:
    svc, _, http = _service()
    http.script_get(MODELS_URL, {"data": []})
    assert svc.current_loaded_id() is None


# ---------------------------------------------------------------------------
# ensure_loaded
# ---------------------------------------------------------------------------


def test_ensure_loaded_noop_when_already_loaded() -> None:
    svc, runner, http = _service()
    http.script_get(MODELS_URL, _models_payload("llama-3.2-1b"))
    svc.ensure_loaded("llama-3.2-1b")
    assert runner.calls == []


def test_ensure_loaded_unloads_and_loads_when_different() -> None:
    svc, runner, http = _service()
    http.script_get(MODELS_URL, _models_payload("old-model"))
    svc.ensure_loaded("new-model")
    assert ("lms", "unload", "--all") in runner.calls
    assert ("lms", "load", "new-model", "-c", "32768", "-y") in runner.calls


def test_ensure_loaded_unload_before_load() -> None:
    svc, runner, http = _service()
    http.script_get(MODELS_URL, _models_payload("old-model"))
    svc.ensure_loaded("new-model")
    unload_idx = runner.calls.index(("lms", "unload", "--all"))
    load_idx = runner.calls.index(("lms", "load", "new-model", "-c", "32768", "-y"))
    assert unload_idx < load_idx


# ---------------------------------------------------------------------------
# bench — metrics extraction
# ---------------------------------------------------------------------------


def _bench_setup(
    *,
    model_id: str = "test-model",
    tps: float = 55.0,
    ttft: float = 0.08,
    reasoning: int = 0,
    content: str = "hello",
    pp_in: int = 128,
    pp_ttft: float = 0.3,
    pp_gen: float = 0.5,
) -> tuple[LMStudioService, FakeProcessRunner, FakeHttpClient]:
    svc, runner, http = _service()
    http.script_get(MODELS_URL, _models_payload(model_id))
    http.script_post(
        COMPLETIONS_URL,
        _tg_payload(tps=tps, ttft=ttft, reasoning=reasoning, content=content),
    )
    # pp uses same URL — FakeHttpClient returns the last scripted post; override with pp payload
    # We need separate scripted responses per call. Use a custom multi-response fake instead.
    return svc, runner, http


def _make_bench_service(
    model_id: str = "test-model",
    *,
    tps: float = 55.0,
    ttft: float = 0.08,
    reasoning: int = 0,
    content: str = "hello world",
    pp_in: int = 128,
    pp_ttft: float = 0.3,
    pp_gen: float = 0.5,
) -> tuple[LMStudioService, FakeProcessRunner, FakeMultiPostHttpClient]:
    runner = FakeProcessRunner()
    http = FakeMultiPostHttpClient()
    http.script_get(MODELS_URL, _models_payload(model_id))
    # warmup response (ignored)
    http.queue_post({})
    # tg response
    http.queue_post(_tg_payload(tps=tps, ttft=ttft, reasoning=reasoning, content=content))
    # pp response
    http.queue_post(_pp_payload(pp_in=pp_in, ttft=pp_ttft, gen=pp_gen))
    svc = LMStudioService(
        runner=runner,
        http=http,
        settings=_settings(),
        which=lambda _: "/usr/local/bin/lms",
    )
    return svc, runner, http


def test_bench_returns_bench_result() -> None:
    svc, _, _ = _make_bench_service()
    result = svc.bench("test-model")
    assert result.model == "test-model"


def test_bench_tg_tps() -> None:
    svc, _, _ = _make_bench_service(tps=72.5)
    assert svc.bench("test-model").tg_tps == pytest.approx(72.5)


def test_bench_ttft() -> None:
    svc, _, _ = _make_bench_service(ttft=0.12)
    assert svc.bench("test-model").ttft == pytest.approx(0.12)


def test_bench_pp_tps_uses_max_of_ttft_and_gen() -> None:
    # pp_wall = max(0.3, 0.5) = 0.5; pp_tps = 128 / 0.5 = 256
    svc, _, _ = _make_bench_service(pp_in=128, pp_ttft=0.3, pp_gen=0.5)
    result = svc.bench("test-model")
    assert result.pp_tps == pytest.approx(256.0)
    assert result.pp_wall == pytest.approx(0.5)


def test_bench_pp_tps_uses_ttft_when_larger() -> None:
    # pp_wall = max(0.8, 0.5) = 0.8; pp_tps = 128 / 0.8 = 160
    svc, _, _ = _make_bench_service(pp_in=128, pp_ttft=0.8, pp_gen=0.5)
    result = svc.bench("test-model")
    assert result.pp_tps == pytest.approx(160.0)


def test_bench_pp_tokens_stored() -> None:
    svc, _, _ = _make_bench_service(pp_in=128)
    assert svc.bench("test-model").pp_tokens == 128


def test_bench_content_len() -> None:
    svc, _, _ = _make_bench_service(content="hello world")
    assert svc.bench("test-model").content_len == len("hello world")


def test_bench_reasoning_tokens() -> None:
    svc, _, _ = _make_bench_service(reasoning=512)
    assert svc.bench("test-model").reasoning_tokens == 512


def test_bench_tier_interactive() -> None:
    svc, _, _ = _make_bench_service(tps=55.0)
    assert svc.bench("test-model").tier == "interactive-grade"


def test_bench_uses_current_model_when_none_given() -> None:
    runner = FakeProcessRunner()
    http = FakeMultiPostHttpClient()
    http.script_get(MODELS_URL, _models_payload("auto-model"))
    http.queue_post({})
    http.queue_post(_tg_payload())
    http.queue_post(_pp_payload())
    svc = LMStudioService(
        runner=runner,
        http=http,
        settings=_settings(),
        which=lambda _: "/usr/local/bin/lms",
    )
    result = svc.bench()
    assert result.model == "auto-model"


def test_bench_raises_when_no_model_and_none_loaded() -> None:
    svc, _, http = _service()
    http.script_get(MODELS_URL, {"data": []})
    with pytest.raises(RuntimeError, match="No model loaded"):
        svc.bench()


def test_bench_sends_warmup_then_tg_then_pp() -> None:
    svc, _, http = _make_bench_service()
    svc.bench("test-model")
    # 3 POSTs: warmup, tg, pp
    assert len(http.posts) == 3
    assert http.posts[0][1]["max_tokens"] == 8  # warmup
    assert http.posts[1][1]["max_tokens"] == 256  # tg
    assert http.posts[2][1]["max_tokens"] == 1  # pp


def test_bench_tg_uses_bench_prompt() -> None:
    svc, _, http = _make_bench_service()
    svc.bench("test-model")
    tg_body = http.posts[1][1]
    assert tg_body["messages"][0]["content"] == BENCH_PROMPT


# ---------------------------------------------------------------------------
# estimate
# ---------------------------------------------------------------------------


def test_estimate_returns_filtered_lines() -> None:
    svc, runner, _ = _service()
    runner.script(
        ("lms", "load", "big-model", "-c", "262144", "--estimate-only", "-y"),
        stdout="Estimated memory usage: 12 GB\nSome other line\nMemory ceiling: 40 GB\n",
    )
    result = svc.estimate("big-model")
    assert "Estimated memory usage" in result
    assert "Some other line" not in result


def test_estimate_uses_default_ctx() -> None:
    svc, runner, _ = _service()
    runner.script(
        ("lms", "load", "big-model", "-c", "262144", "--estimate-only", "-y"),
        stdout="Estimated memory: 8 GB\n",
    )
    svc.estimate("big-model")
    assert ("lms", "load", "big-model", "-c", "262144", "--estimate-only", "-y") in runner.calls


def test_estimate_uses_provided_ctx() -> None:
    svc, runner, _ = _service()
    runner.script(
        ("lms", "load", "big-model", "-c", "65536", "--estimate-only", "-y"),
        stdout="Estimated memory: 6 GB\n",
    )
    svc.estimate("big-model", 65536)
    assert ("lms", "load", "big-model", "-c", "65536", "--estimate-only", "-y") in runner.calls


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------


def test_random_words_returns_n_words() -> None:
    words = _random_words(128)
    assert len(words.split()) == 128


def test_random_words_all_lowercase_ascii() -> None:
    words = _random_words(10)
    for ch in words.replace(" ", ""):
        assert ch.islower()


def test_is_estimate_line_matches_estimate() -> None:
    assert _is_estimate_line("Estimated memory usage: 12 GB")


def test_is_estimate_line_matches_memory() -> None:
    assert _is_estimate_line("Memory ceiling: 40 GB")


def test_is_estimate_line_rejects_other() -> None:
    assert not _is_estimate_line("Loading model weights...")
