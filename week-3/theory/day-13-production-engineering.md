[← Day 12](../../week-3/theory/day-12-safety-and-guardrails.md) · [Week 3 overview](../README.md) · [▶️ Practice notebook](../practice/day-13-production.ipynb) · [Day 14 →](../../week-3/theory/day-14-frameworks.md)

## Day 13 — Production engineering & optimization (reliability, observability, cost, latency)

⏱ 75 min theory · 30 min lab · 60 min capstone

**Goals:** add tracing, retries, timeouts and idempotency; then apply the main cost and latency levers with numbers to back them.


### 🎥 Watch first (short videos)
- 🎥 [LLM Observability: Traces, Spans & OpenTelemetry for AI Apps](https://www.youtube.com/watch?v=c4mDP5Qp7iM): *community explainer*. what to trace and why
- 🎥 [What is Prompt Caching? (re-watch)](https://www.youtube.com/watch?v=axuTuZ9ERv8): *community explainer*. the #1 cost lever

> Durations are approximate. "Community explainer" means an independent creator; the written links in each section are the primary sources.

### 13.1 Observability: you can't fix what you can't see

**Intuition.** A trace is the flight recorder of one agent run: every LLM call and tool call as nested *spans* with inputs, outputs, tokens, cost and latency.

```
trace: conversation c-81 (4.2s, $0.031)
├── llm.call  step=1  in=3.1k (2.9k cached)  out=210   1.1s
├── tool      get_customer_overview  38ms
├── llm.call  step=2  in=3.6k (3.3k cached)  out=95    0.8s
├── tool      check_refund_eligibility  12ms
└── llm.call  step=3  in=3.8k (3.6k cached)  out=180   1.2s
```

A minimal tracer to start with, before moving to OpenTelemetry/Langfuse:

```python
import time, json, uuid, functools
TRACE = []
def traced(kind):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            t0 = time.perf_counter(); span = {"id": uuid.uuid4().hex[:8], "kind": kind, "name": fn.__name__}
            try:
                out = fn(*a, **kw); span["ok"] = True; return out
            except Exception as e:
                span["ok"] = False; span["error"] = str(e); raise
            finally:
                span["ms"] = round((time.perf_counter() - t0) * 1000); TRACE.append(span)
        return wrapper
    return deco
```

**Production stack:** OpenTelemetry spans (GenAI semantic conventions) → a backend like **Langfuse** (open source, free tier), or your existing APM. Log `usage` on every call and tag traces with `conversation_id`, `customer_tier`, `route` and `prompt_version`.

📖 Deep dive: 📘 [Langfuse — OpenTelemetry tracing](https://langfuse.com/docs/opentelemetry/get-started)

### 13.2 Reliability patterns

| Problem | Pattern | Detail |
|---|---|---|
| API 429/5xx/timeouts | **Retry with exponential backoff + jitter** | The SDK retries 2× by default (`max_retries`); add retries for *your* tools |
| Slow calls | **Timeouts** at every layer | `anthropic.Anthropic(timeout=60)`; tool timeouts; a whole-run deadline |
| Retry causes double refunds | **Idempotency keys** | `refund(order_id, key=f"{conversation_id}:{order_id}")` and dedupe in the DB |
| Provider outage / refusal | **Fallbacks** | Server-side `fallbacks` (beta), or catch and retry on another model |
| Bad tool output crashes the loop | **Errors as results** | `is_error: True`, never an exception that kills the run |
| Runaway agent | **Budgets** | Steps, cost, time (Day 3) |

```python
import random, time
def with_retries(fn, *args, attempts=4, base=0.5, **kw):
    for i in range(attempts):
        try:
            return fn(*args, **kw)
        except (TimeoutError, ConnectionError):
            if i == attempts - 1: raise
            time.sleep(base * 2 ** i + random.uniform(0, base))     # backoff + jitter
```

### 13.3 Cost optimization levers, in order (free wins first)

| # | Lever | Typical effect | Trade-off |
|---|---|---|---|
| 1 | **Prompt caching** (Day 5) | 50–90% off repeated input | None if the prefix is stable |
| 2 | **Context hygiene:** truncate tool output, trim history | Large on long runs | Possible info loss |
| 3 | **Routing:** easy traffic to cheap paths (Day 4) | Often the biggest saving | Misroutes; needs a router eval |
| 4 | **Effort tuning** per route | Fewer thinking/output tokens | Quality on hard cases; measure it |
| 5 | **Smaller model for subtasks** (judges, summaries, subagents) | 10–40× cheaper per token | Quality on those subtasks |
| 6 | **Batch API** for offline work (evals, backfills) | ~50% off | Async results (not real-time) |
| 7 | Output length limits ("answer in ≤120 words") | Fewer output tokens (5× price) | Terser replies |

**Cascade math (try cheap, escalate if needed).** With cheap-model cost `c_s`, expensive cost `c_b`, and fraction `a` of cases the cheap path handles acceptably (verified by a check):

$$E[\text{cost}] = c_s + (1-a)\,c_b \quad\text{vs}\quad c_b \qquad\Rightarrow\quad \text{cascade wins if } c_s < a\,c_b$$

Example: c_s = $0.002, c_b = $0.04, a = 0.7 ⇒ E = 0.002 + 0.3 × 0.04 = **$0.014** (65% saving). It's only valid if the *check* that decides whether to escalate is reliable, so measure it with evals.

> 💡 Before building a multi-model cascade, try the strong model at **lower effort** first. It often matches older setups at lower cost, keeps a single cache namespace, and is less code.

**Judge cost per *completed task*, not per call.** A cheap call that needs 3 retries isn't cheap.

```python
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

batch = client.messages.batches.create(requests=[
    Request(custom_id=c["id"], params=MessageCreateParamsNonStreaming(
        model=CHEAP_MODEL, max_tokens=1000, messages=[{"role": "user", "content": c["input"]}]))
    for c in cases])
# poll client.messages.batches.retrieve(batch.id).processing_status until "ended", then read results by custom_id
```

📖 Deep dive: 📘 [Claude docs — Batch processing](https://platform.claude.com/docs/en/build-with-claude/batch-processing)

### 13.4 Latency levers

What users feel is **time to first token** (TTFT) and total time. Agent latency ≈ Σ(LLM call time) + Σ(tool time), so fewer, faster steps win.

| Lever | Helps | Note |
|---|---|---|
| **Streaming** | Perceived latency (TTFT) | Show text as it's generated; show "checking your order…" during tools |
| **Caching** | TTFT on long prefixes | Cached prefixes are processed much faster |
| **Parallel tool calls** (Day 2) | Total time | Run independent tools concurrently |
| **Fewer steps** | Total time | Better tools (one `get_customer_overview` instead of 3 calls), lower effort |
| **Router fast path** | Total time for easy traffic | FAQ answers without the agent loop |
| Fast mode / smaller models | Output speed | Premium pricing or quality trade-offs |

### 🧪 Lab → do it in the practice notebook 13 — Optimization sprint (30 min)
Take the capstone and run the eval suite as a baseline (pass rate, $ per conversation, p50/p95 latency). Apply 3 levers one at a time (caching, effort per route, Haiku judge via Batch) and re-run evals after each. Present a before/after table. A lever counts only if quality holds.

### 🏗 Capstone — Day 13
Add tracing on every LLM and tool call (OpenTelemetry → Langfuse, or the minimal tracer), retries, timeouts, idempotent refunds and a model fallback. `report.md` now includes cost per conversation, cache hit rate, p50/p95 latency and steps per conversation.

### ✅ Checkpoint
1. Why do agent retries need idempotency keys?
2. Compute the cascade cost for c_s = $0.001, c_b = $0.03, a = 0.6. Is it worth it?
3. List the cost levers in the order you'd try them, and why that order.
4. What's TTFT, and which two levers improve it most?

---

**Next:** open the [practice notebook](../practice/day-13-production.ipynb) · capstone milestone in [projects/shopease-support-agent](../../projects/shopease-support-agent/README.md#milestones-build-your-own-version-alongside-the-course)

[← Day 12](../../week-3/theory/day-12-safety-and-guardrails.md) · [Week 3 overview](../README.md) · [▶️ Practice notebook](../practice/day-13-production.ipynb) · [Day 14 →](../../week-3/theory/day-14-frameworks.md)
