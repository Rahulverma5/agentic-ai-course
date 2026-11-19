"""Track tokens and dollars for every call. Prices are approximate: check the pricing page."""
from __future__ import annotations

from dataclasses import dataclass, field

# $ per 1M tokens: (input, output, cache_read). Cache writes ≈ 1.25 × input (5-minute cache).
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),  # ≤100K-token prompts; check the pricing page
}
CACHE_WRITE_MULTIPLIER = 1.25


@dataclass
class CostTracker:
    calls: list = field(default_factory=list)

    def add(self, model: str, usage, label: str = "") -> float:
        """Record one response's usage. Returns that call's cost in $."""
        price_in, price_out, price_cache = PRICES.get(model, (0.0, 0.0, 0.0))
        g = lambda name: getattr(usage, name, 0) or 0  # noqa: E731
        cost = (g("input_tokens") * price_in
                + g("cache_creation_input_tokens") * price_in * CACHE_WRITE_MULTIPLIER
                + g("cache_read_input_tokens") * price_cache
                + g("output_tokens") * price_out) / 1e6
        self.calls.append({
            "label": label, "model": model, "input": g("input_tokens"), "output": g("output_tokens"),
            "cache_write": g("cache_creation_input_tokens"), "cache_read": g("cache_read_input_tokens"),
            "cost": cost,
        })
        return cost

    def total(self) -> float:
        return sum(c["cost"] for c in self.calls)

    def summary(self) -> str:
        n = len(self.calls)
        inp = sum(c["input"] + c["cache_read"] + c["cache_write"] for c in self.calls)
        out = sum(c["output"] for c in self.calls)
        return f"{n} calls · {inp:,} input tokens · {out:,} output tokens · ${self.total():.4f}"

    def to_dataframe(self):
        import pandas as pd

        return pd.DataFrame(self.calls)

    def reset(self):
        self.calls.clear()


tracker = CostTracker()  # shared by ask() and run_agent()
