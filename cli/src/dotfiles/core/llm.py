"""LMStudioService: core logic for llm-bench subcommands.

Ports injected: ProcessRunner, HttpClient, LlmSettings.
No subprocess or network calls here — all I/O goes through ports.
"""

import random
import shutil
import string
from collections.abc import Callable
from typing import Any, cast

from dotfiles.core.models import BenchResult
from dotfiles.core.ports import HttpClient, ProcessRunner
from dotfiles.core.settings import LlmSettings

BENCH_PROMPT = (
    "Write a Python function `first_n_primes(n)` returning the first N prime numbers "
    "using the Sieve of Eratosthenes. Include a brief docstring and one test case. "
    "Keep it under 20 lines total."
)

_WhichFn = Callable[[str], str | None]


class LMStudioService:
    """Core logic for interacting with LM Studio via lms CLI + HTTP API."""

    def __init__(
        self,
        *,
        runner: ProcessRunner,
        http: HttpClient,
        settings: LlmSettings,
        which: _WhichFn = shutil.which,
    ) -> None:
        self._runner = runner
        self._http = http
        self._s = settings
        self._which = which

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def list_loaded(self) -> str:
        """Return raw `lms ps` output (passthrough)."""
        self._require_lms()
        return self._runner.run(("lms", "ps")).stdout

    def current_loaded_id(self) -> str | None:
        """Return the ID of the first loaded model, or None."""
        resp: Any = self._http.get_json(f"{self._s.lms_host}/api/v0/models")
        for item in cast(list[Any], resp.get("data", [])):
            if item.get("state") == "loaded":
                return str(item["id"])
        return None

    def ensure_loaded(self, model: str) -> None:
        """Unload all and load *model* if it isn't already loaded."""
        if self.current_loaded_id() != model:
            self._runner.run(("lms", "unload", "--all"))
            self._runner.run(("lms", "load", model, "-c", str(self._s.load_ctx), "-y"))

    def bench(self, model: str | None = None) -> BenchResult:
        """Run the full bench sequence and return metrics."""
        model = self._resolve_model(model)
        self._warmup(model)
        tg_resp = self._token_gen(model)
        pp_resp = self._prompt_eval(model)
        return self._metrics(model, tg_resp, pp_resp)

    def estimate(self, model: str, ctx: int | None = None) -> str:
        """Return memory estimate output from `lms load --estimate-only`."""
        ctx_val = ctx if ctx is not None else 262144
        result = self._runner.run(
            ("lms", "load", model, "-c", str(ctx_val), "--estimate-only", "-y")
        )
        lines = [ln for ln in result.stdout.splitlines() if _is_estimate_line(ln)]
        return "\n".join(lines[:3])

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _require_lms(self) -> None:
        if not self._which("lms"):
            raise RuntimeError("lms CLI not found. Install LM Studio and run 'lms bootstrap'.")

    def _resolve_model(self, model: str | None) -> str:
        if model:
            self.ensure_loaded(model)
            return model
        loaded = self.current_loaded_id()
        if not loaded:
            raise RuntimeError("No model loaded. Pass MODEL_ID or load one first.")
        return loaded

    def _completions_url(self) -> str:
        return f"{self._s.lms_host}/api/v0/chat/completions"

    def _warmup(self, model: str) -> None:
        self._http.post_json(
            self._completions_url(),
            {
                "model": model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 8,
                "temperature": 0,
            },
        )

    def _token_gen(self, model: str) -> Any:
        return self._http.post_json(
            self._completions_url(),
            {
                "model": model,
                "messages": [{"role": "user", "content": BENCH_PROMPT}],
                "max_tokens": self._s.tg_tokens,
                "temperature": 0,
                "stream": False,
            },
        )

    def _prompt_eval(self, model: str) -> Any:
        prompt = _random_words(self._s.pp_tokens)
        return self._http.post_json(
            self._completions_url(),
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1,
                "temperature": 0,
                "stream": False,
            },
        )

    def _metrics(self, model: str, tg: Any, pp: Any) -> BenchResult:
        tg_stats = tg.get("stats", {})
        pp_stats = pp.get("stats", {})

        tg_tps: float = tg_stats.get("tokens_per_second", 0) or 0
        ttft: float = tg_stats.get("time_to_first_token", 0) or 0
        reasoning: int = (
            tg.get("usage", {}).get("completion_tokens_details", {}).get("reasoning_tokens", 0) or 0
        )
        choices: list[Any] = tg.get("choices") or [{}]
        content: str = choices[0].get("message", {}).get("content", "") or ""
        content_len: int = len(content)

        pp_ttft: float = pp_stats.get("time_to_first_token", 0) or 0
        pp_gen: float = pp_stats.get("generation_time", 0) or 0
        pp_in: int = pp.get("usage", {}).get("prompt_tokens", 0) or 0
        pp_wall = max(pp_ttft, pp_gen)
        pp_tps = (pp_in / pp_wall) if pp_wall > 0 and pp_in > 0 else 0.0

        return BenchResult(
            model=model,
            tg_tps=tg_tps,
            pp_tps=pp_tps,
            pp_tokens=pp_in,
            pp_wall=pp_wall,
            ttft=ttft,
            reasoning_tokens=reasoning,
            content_len=content_len,
        )


# ------------------------------------------------------------------
# Module-level helpers (no side effects, easy to monkeypatch)
# ------------------------------------------------------------------


def _random_words(n: int) -> str:
    """Return n space-separated random lowercase ASCII words (single chars)."""
    return " ".join(random.choices(string.ascii_lowercase, k=n))


def _is_estimate_line(line: str) -> bool:
    low = line.lower()
    return "estimate" in low or "memory" in low
