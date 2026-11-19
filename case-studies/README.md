# Case studies: how real teams build agents

Each case study takes one published, first-hand engineering write-up and turns it into a lesson with the same structure:

**TL;DR → context → architecture → decisions & trade-offs → numbers worth remembering → what to apply to ShopEase → discussion questions → sources**

Numbers are quoted from the linked sources and are reported by those authors, not independently reproduced. Read the original after the summary.

| # | Case study | Core lesson | Pairs with |
|---|---|---|---|
| 01 | [Anthropic's multi-agent research system](01-anthropic-multi-agent-research.md) | Parallel subagents win on breadth-first, read-only work, at ~15× chat tokens | Day 9 |
| 02 | [Cognition: single-threaded agents](02-cognition-single-threaded-agents.md) | Context sharing beats agent count; many readers, one writer | Days 5, 9 |
| 03 | [The Claude Code agent loop](03-claude-code-agent-loop.md) | One simple loop + great tools + context management | Days 3, 5, 14 |
| 04 | [Contextual Retrieval](04-contextual-retrieval.md) | Fix "orphaned" chunks; hybrid + rerank; cache makes it cheap | Day 6 |
| 05 | [Code execution with MCP](05-code-execution-with-mcp.md) | Present tools as code; keep data out of the context | Days 8, 10 |
| 06 | [Harnesses for long-running agents](06-long-running-agent-harnesses.md) | Progress files, feature lists, one increment per session | Days 7, 15 |
| 07 | [Customer-service agents & τ-bench](07-customer-service-agents-tau-bench.md) | Policy-following + consistency (pass^k) is the real bar | Days 11, capstone |
| 08 | [Prompt injection & the lethal trifecta](08-prompt-injection-lethal-trifecta.md) | Architecture limits damage; filters don't | Day 12 |

**How to use them:** read one per day in Week 2–3 (~20 min). Answer the discussion questions in writing. Then apply one lesson to your capstone and measure it with the eval suite.
