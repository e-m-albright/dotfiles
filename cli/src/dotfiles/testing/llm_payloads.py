"""Shared LM Studio API payload builders for the llm tests.

Mirrors the shapes LMStudioService validates (LmsModelsResponse / LmsCompletion).
Used by both test_llm_core and test_cli_llm so the fixtures can't drift apart.
"""

from __future__ import annotations

from typing import Any


def models_payload(model_id: str, state: str = "loaded") -> dict[str, Any]:
    return {"data": [{"id": model_id, "state": state}]}


def tg_payload(
    *,
    tps: float = 55.0,
    ttft: float = 0.08,
    reasoning: int = 0,
    content: str = "def first_n_primes(n): ...",
    completion_tokens: int = 50,
) -> dict[str, Any]:
    return {
        "stats": {
            "tokens_per_second": tps,
            "time_to_first_token": ttft,
            "generation_time": 0.9,
        },
        "usage": {
            "completion_tokens": completion_tokens,
            "completion_tokens_details": {"reasoning_tokens": reasoning},
        },
        "choices": [{"message": {"content": content}}],
    }


def pp_payload(*, pp_in: int = 128, ttft: float = 0.3, gen: float = 0.5) -> dict[str, Any]:
    return {
        "stats": {"time_to_first_token": ttft, "generation_time": gen},
        "usage": {"prompt_tokens": pp_in},
        "choices": [{"message": {"content": "x"}}],
    }
