"""Domain models for local-LLM benchmarking."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

ThroughputTier = Literal["autocomplete-grade", "interactive-grade", "tolerable", "painful"]


class BenchResult(BaseModel):
    """Metrics from a single LM Studio bench run."""

    model_config = ConfigDict(frozen=True)

    model: str
    tg_tps: float
    pp_tps: float
    pp_tokens: int
    pp_wall: float
    ttft: float
    reasoning_tokens: int
    content_len: int

    @property
    def tier(self) -> ThroughputTier:
        """Classify token-gen throughput, matching llm-bench.sh classify()."""
        if self.tg_tps >= 100:
            return "autocomplete-grade"
        if self.tg_tps >= 40:
            return "interactive-grade"
        if self.tg_tps >= 20:
            return "tolerable"
        return "painful"
