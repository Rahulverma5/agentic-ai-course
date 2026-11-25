"""Track tokens and (estimated) dollars for every Gemini call.

On the free tier you pay $0. The tracker still shows what the same usage would cost at paid prices,
so you learn to reason about cost. Prices below are APPROXIMATE and change often: check
https://ai.google.dev/gemini-api/docs/pricing and adjust PRICES (or add your pinned model ids).
"""
from __future__ import annotations

from dataclasses import dataclass, field

# $ per 1M tokens: (input, output incl. thinking, cached input)
PRICES = {
    "gemini-flash-latest": (1.50, 7.50, 0.15),
    "gemini-flash-lite-latest": (0.30, 2.50, 0.03),
}


def _price(model: str):
    if model in PRICES:
        return PRICES[model]
    if "lite" in model:
        return PRICES["gemini-flash-lite-latest"]
    if "flash" in model:
        return PRICES["gemini-flash-latest"]
    return (0.0, 0.0, 0.0)


@dataclass
class CostTracker:
    calls: list = field(default_factory=list)

    def add(self, model: str, usage, label: str = "") -> float:
        """Record one response's usage_metadata. Returns the estimated cost in $."""
        g = lambda name: (getattr(usage, name, 0) or 0) if usage else 0  # noqa: E731
        prompt, cached = g("prompt_token_count"), g("cached_content_token_count")
        output, thoughts = g("candidates_token_count"), g("thoughts_token_count")
        price_in, price_out, price_cache = _price(model)
        cost = ((prompt - cached) * price_in + cached * price_cache + (output + thoughts) * price_out) / 1e6
        self.calls.append({"label": label, "model": model, "input": prompt, "cached": cached,
                           "output": output, "thinking": thoughts, "cost": cost})
        return cost

    def total(self) -> float:
        return sum(c["cost"] for c in self.calls)

    def summary(self) -> str:
        n = len(self.calls)
        inp = sum(c["input"] for c in self.calls)
        cached = sum(c["cached"] for c in self.calls)
        out = sum(c["output"] + c["thinking"] for c in self.calls)
        return (f"{n} calls · {inp:,} input tokens ({cached:,} cached) · {out:,} output+thinking tokens · "
                f"≈${self.total():.4f} at paid prices ($0 on the free tier)")

    def to_dataframe(self):
        import pandas as pd

        return pd.DataFrame(self.calls)

    def reset(self):
        self.calls.clear()


tracker = CostTracker()  # shared by ask() and run_agent()
