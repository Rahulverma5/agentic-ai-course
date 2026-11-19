# Week 1 — Foundations: the loop, the tools, the patterns

**Goal:** by the end of the week you can build a single-agent system from scratch: tools, the agent loop, workflow patterns, context and caching, RAG and memory. You'll understand how each piece evolved and when to use it.

| Day | 📖 Theory (~60 min) | 🧪 Practice (~60–90 min) | Key idea |
|---|---|---|---|
| 1 | [What an agent is & how we got here](theory/day-01-what-is-an-agent.md) | [Tokens & cost](practice/day-01-tokens-and-cost.ipynb) | Workflow vs agent; cost grows ~quadratically with steps |
| 2 | [Tool calling & structured outputs](theory/day-02-tool-calling.md) | [Tool calling](practice/day-02-tool-calling.ipynb) | The model asks, *your code* runs; tool design = UI for the model |
| 3 | [Agent loop, reasoning & planning](theory/day-03-agent-loop-and-planning.md) | [Agent loop](practice/day-03-agent-loop.ipynb) | Think → act → observe, with budgets |
| 4 | [Workflow patterns](theory/day-04-workflow-patterns.md) | [Workflow patterns](practice/day-04-workflow-patterns.ipynb) | Chaining, routing, parallel, orchestrator, evaluator |
| 5 | [Context engineering & caching](theory/day-05-context-engineering-and-caching.md) | [Context & caching](practice/day-05-context-and-caching.ipynb) | Lean context; stable prefix → big savings |
| 6 | [RAG for agents](theory/day-06-rag-for-agents.md) | [Hybrid RAG](practice/day-06-rag.ipynb) | BM25 + vectors + RRF; measure recall@k |
| 7 | [Memory](theory/day-07-memory.md) | [Memory](practice/day-07-memory.ipynb) | What to store, what to forget, poisoning |

**How to study each day:** watch the short videos at the top of the theory note → read the note → run the notebook top to bottom → do the exercises at the end → add the day's milestone to the [ShopEase capstone](../projects/shopease-support-agent/README.md).

**Warm-up (optional, before Day 3):** [projects/file-assistant](../projects/file-assistant/).
