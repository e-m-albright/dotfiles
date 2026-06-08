"""Tests for `dotfiles llm` Typer commands (list/bench/estimate/compare)."""

from typer.testing import CliRunner

from dotfiles.app.main import app
from dotfiles.testing.fakes import (
    FakeHttpClient,
    FakeMultiPostHttpClient,
    FakeProcessRunner,
    make_fake_context,
)
from dotfiles.testing.llm_payloads import models_payload as _models_payload
from dotfiles.testing.llm_payloads import pp_payload as _pp_payload
from dotfiles.testing.llm_payloads import tg_payload as _tg_payload

runner = CliRunner()

# ---------------------------------------------------------------------------
# URL constants (must match LlmSettings defaults)
# ---------------------------------------------------------------------------

MODELS_URL = "http://localhost:1234/api/v0/models"
COMPLETIONS_URL = "http://localhost:1234/api/v0/chat/completions"


def _bench_http(
    *,
    model_id: str = "test-model",
    tps: float = 55.0,
    ttft: float = 0.08,
    reasoning: int = 0,
    content: str = "hello world",
    pp_in: int = 128,
) -> FakeMultiPostHttpClient:
    """Build a scripted HTTP client for a full bench sequence."""
    http = FakeMultiPostHttpClient()
    http.script_get(MODELS_URL, _models_payload(model_id))
    http.queue_post({})  # warmup (ignored)
    http.queue_post(_tg_payload(tps=tps, ttft=ttft, reasoning=reasoning, content=content))
    http.queue_post(_pp_payload(pp_in=pp_in))
    return http


# ---------------------------------------------------------------------------
# llm --help
# ---------------------------------------------------------------------------


def test_llm_help_exits_zero() -> None:
    result = runner.invoke(app, ["benchmark", "--help"])
    assert result.exit_code == 0, result.output


def test_llm_help_lists_list_subcommand() -> None:
    result = runner.invoke(app, ["benchmark", "--help"])
    assert "list" in result.output


def test_llm_help_lists_bench_subcommand() -> None:
    result = runner.invoke(app, ["benchmark", "--help"])
    assert "bench" in result.output


def test_llm_help_lists_estimate_subcommand() -> None:
    result = runner.invoke(app, ["benchmark", "--help"])
    assert "estimate" in result.output


def test_llm_help_lists_compare_subcommand() -> None:
    result = runner.invoke(app, ["benchmark", "--help"])
    assert "compare" in result.output


# ---------------------------------------------------------------------------
# llm list
# ---------------------------------------------------------------------------


def test_llm_list_prints_lms_ps_output() -> None:
    """lms is on PATH on this machine; FakeProcessRunner scripts (lms, ps) output."""
    proc = FakeProcessRunner()
    proc.script(("lms", "ps"), stdout="my-model  loaded\n")
    ctx = make_fake_context(runner=proc)
    result = runner.invoke(app, ["benchmark", "list"], obj=ctx)
    # lms is installed, so we expect the scripted output to be printed
    assert result.exit_code == 0, result.output
    assert "my-model" in result.output


def test_llm_list_exit_zero() -> None:
    proc = FakeProcessRunner()
    proc.script(("lms", "ps"), stdout="model-a  loaded\n")
    ctx = make_fake_context(runner=proc)
    result = runner.invoke(app, ["benchmark", "list"], obj=ctx)
    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# llm bench
# ---------------------------------------------------------------------------


def test_llm_bench_exits_zero() -> None:
    http = _bench_http(model_id="test-model", tps=55.0)
    ctx = make_fake_context(http=http)
    result = runner.invoke(app, ["benchmark", "bench", "test-model"], obj=ctx)
    assert result.exit_code == 0, result.output


def test_llm_bench_output_contains_throughput() -> None:
    http = _bench_http(model_id="test-model", tps=55.0)
    ctx = make_fake_context(http=http)
    result = runner.invoke(app, ["benchmark", "bench", "test-model"], obj=ctx)
    assert "Throughput" in result.output


def test_llm_bench_output_contains_tier_label() -> None:
    """tg tps=55 → interactive-grade tier."""
    http = _bench_http(model_id="test-model", tps=55.0)
    ctx = make_fake_context(http=http)
    result = runner.invoke(app, ["benchmark", "bench", "test-model"], obj=ctx)
    assert "interactive-grade" in result.output


def test_llm_bench_output_contains_tps_value() -> None:
    http = _bench_http(model_id="test-model", tps=72.5)
    ctx = make_fake_context(http=http)
    result = runner.invoke(app, ["benchmark", "bench", "test-model"], obj=ctx)
    assert "72.50" in result.output


def test_llm_bench_output_contains_ttft() -> None:
    http = _bench_http(model_id="test-model", ttft=0.123)
    ctx = make_fake_context(http=http)
    result = runner.invoke(app, ["benchmark", "bench", "test-model"], obj=ctx)
    assert "TTFT" in result.output
    assert "0.123" in result.output


def test_llm_bench_reasoning_tokens_shown() -> None:
    http = _bench_http(model_id="test-model", reasoning=0)
    ctx = make_fake_context(http=http)
    result = runner.invoke(app, ["benchmark", "bench", "test-model"], obj=ctx)
    assert "Reasoning tokens" in result.output


def test_llm_bench_thinking_model_detected() -> None:
    """reasoning_tokens > 0 → output contains THINKING MODEL."""
    http = _bench_http(model_id="think-model", reasoning=512)
    ctx = make_fake_context(http=http)
    result = runner.invoke(app, ["benchmark", "bench", "think-model"], obj=ctx)
    assert "THINKING MODEL" in result.output


def test_llm_bench_non_reasoning_model_no_thinking_label() -> None:
    http = _bench_http(model_id="plain-model", reasoning=0)
    ctx = make_fake_context(http=http)
    result = runner.invoke(app, ["benchmark", "bench", "plain-model"], obj=ctx)
    assert "THINKING MODEL" not in result.output


def test_llm_bench_no_model_arg_uses_loaded() -> None:
    """bench without model ID uses the currently loaded model via /api/v0/models."""
    http = _bench_http(model_id="auto-model", tps=45.0)
    ctx = make_fake_context(http=http)
    result = runner.invoke(app, ["benchmark", "bench"], obj=ctx)
    assert result.exit_code == 0, result.output
    assert "Throughput" in result.output


def test_llm_bench_no_model_no_loaded_exits_one() -> None:
    http = FakeHttpClient()
    http.script_get(MODELS_URL, {"data": []})
    ctx = make_fake_context(http=http)
    result = runner.invoke(app, ["benchmark", "bench"], obj=ctx)
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# llm estimate
# ---------------------------------------------------------------------------


def test_llm_estimate_exits_zero() -> None:
    proc = FakeProcessRunner()
    proc.script(
        ("lms", "load", "big-model", "-c", "262144", "--estimate-only", "-y"),
        stdout="Estimated memory usage: 12 GB\n",
    )
    ctx = make_fake_context(runner=proc)
    result = runner.invoke(app, ["benchmark", "estimate", "big-model"], obj=ctx)
    assert result.exit_code == 0, result.output


def test_llm_estimate_output_contains_estimate_line() -> None:
    proc = FakeProcessRunner()
    proc.script(
        ("lms", "load", "big-model", "-c", "262144", "--estimate-only", "-y"),
        stdout="Estimated memory usage: 12 GB\nSome other line\n",
    )
    ctx = make_fake_context(runner=proc)
    result = runner.invoke(app, ["benchmark", "estimate", "big-model"], obj=ctx)
    assert "Estimated memory usage" in result.output


def test_llm_estimate_prints_ceiling_note() -> None:
    proc = FakeProcessRunner()
    proc.script(
        ("lms", "load", "big-model", "-c", "262144", "--estimate-only", "-y"),
        stdout="Estimated memory usage: 12 GB\n",
    )
    ctx = make_fake_context(runner=proc)
    result = runner.invoke(app, ["benchmark", "estimate", "big-model"], obj=ctx)
    assert "40 GB" in result.output


# ---------------------------------------------------------------------------
# llm compare
# ---------------------------------------------------------------------------


def test_llm_compare_exits_zero() -> None:
    # compare benches both models; build a multi-response client for the full sequence
    http = FakeMultiPostHttpClient()
    # model-a GET (ensure_loaded checks)
    http.script_get(MODELS_URL, _models_payload("model-a"))
    # model-a: warmup, tg, pp
    http.queue_post({})
    http.queue_post(_tg_payload(tps=55.0))
    http.queue_post(_pp_payload())
    # model-b: warmup, tg, pp (GET still returns model-a state — ensure_loaded will trigger load)
    http.queue_post({})
    http.queue_post(_tg_payload(tps=80.0))
    http.queue_post(_pp_payload())

    proc = FakeProcessRunner()
    proc.script(("lms", "unload", "--all"), stdout="")
    proc.script(("lms", "load", "model-b", "-c", "32768", "-y"), stdout="")

    ctx = make_fake_context(runner=proc, http=http)
    result = runner.invoke(app, ["benchmark", "compare", "model-a", "model-b"], obj=ctx)
    assert result.exit_code == 0, result.output


def test_llm_compare_output_contains_head_to_head() -> None:
    http = FakeMultiPostHttpClient()
    http.script_get(MODELS_URL, _models_payload("model-a"))
    http.queue_post({})
    http.queue_post(_tg_payload(tps=55.0))
    http.queue_post(_pp_payload())
    http.queue_post({})
    http.queue_post(_tg_payload(tps=80.0))
    http.queue_post(_pp_payload())

    proc = FakeProcessRunner()
    proc.script(("lms", "unload", "--all"), stdout="")
    proc.script(("lms", "load", "model-b", "-c", "32768", "-y"), stdout="")

    ctx = make_fake_context(runner=proc, http=http)
    result = runner.invoke(app, ["benchmark", "compare", "model-a", "model-b"], obj=ctx)
    assert "model-a vs model-b" in result.output  # the title-rule matchup line


def test_llm_compare_output_contains_both_throughput_blocks() -> None:
    http = FakeMultiPostHttpClient()
    http.script_get(MODELS_URL, _models_payload("model-a"))
    http.queue_post({})
    http.queue_post(_tg_payload(tps=55.0))
    http.queue_post(_pp_payload())
    http.queue_post({})
    http.queue_post(_tg_payload(tps=80.0))
    http.queue_post(_pp_payload())

    proc = FakeProcessRunner()
    proc.script(("lms", "unload", "--all"), stdout="")
    proc.script(("lms", "load", "model-b", "-c", "32768", "-y"), stdout="")

    ctx = make_fake_context(runner=proc, http=http)
    result = runner.invoke(app, ["benchmark", "compare", "model-a", "model-b"], obj=ctx)
    assert result.output.count("Throughput") == 2


def test_llm_output_with_brackets_not_eaten_by_rich_markup() -> None:
    # A model/estimate string containing brackets must survive Rich markup
    # rendering verbatim (regression guard for markup=False / escape()).
    proc = FakeProcessRunner()
    proc.script(
        ("lms", "load", "qwen[Q4_K_M]", "-c", "262144", "--estimate-only", "-y"),
        stdout="Memory estimate: 12.5 GB [max]\n",
    )
    ctx = make_fake_context(runner=proc)
    result = runner.invoke(app, ["benchmark", "estimate", "qwen[Q4_K_M]"], obj=ctx)
    assert result.exit_code == 0, result.output
    assert "[max]" in result.output
