"""A minimal tracer: nested spans with timing and attributes, written as JSON lines.

Swap for OpenTelemetry + Langfuse in production (Day 13); the span shape is the same idea.
"""
from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager

from . import config


class Tracer:
    def __init__(self, trace_id: str | None = None, enabled: bool = True):
        self.trace_id = trace_id or uuid.uuid4().hex[:12]
        self.enabled = enabled
        self.spans: list[dict] = []
        self._stack: list[str] = []

    @contextmanager
    def span(self, kind: str, name: str, **attrs):
        span = {"trace_id": self.trace_id, "id": uuid.uuid4().hex[:8], "parent": self._stack[-1] if self._stack else None,
                "kind": kind, "name": name, "attrs": attrs, "start": time.time()}
        self._stack.append(span["id"])
        try:
            yield span["attrs"]  # callers can add attributes: `with tracer.span(...) as a: a["tokens"] = 5`
            span["ok"] = True
        except Exception as e:
            span["ok"], span["error"] = False, f"{type(e).__name__}: {e}"
            raise
        finally:
            span["ms"] = round((time.time() - span["start"]) * 1000)
            self._stack.pop()
            if self.enabled:
                self.spans.append(span)

    def save(self) -> str | None:
        if not self.enabled or not self.spans:
            return None
        config.TRACE_DIR.mkdir(parents=True, exist_ok=True)
        path = config.TRACE_DIR / f"{self.trace_id}.jsonl"
        with path.open("a") as f:
            for s in self.spans:
                f.write(json.dumps(s, default=str) + "\n")
        self.spans.clear()
        return str(path)

    def pretty(self) -> str:
        depth, lines = {}, []
        for s in sorted(self.spans, key=lambda s: s["start"]):
            d = depth[s["id"]] = depth.get(s["parent"], -1) + 1
            extra = " ".join(f"{k}={v}" for k, v in s["attrs"].items())
            lines.append(f"{'  ' * d}├─ {s['kind']:<6} {s['name']:<28} {s['ms']:>6} ms  {extra}{'' if s.get('ok', True) else ' ❌'}")
        return "\n".join(lines)
