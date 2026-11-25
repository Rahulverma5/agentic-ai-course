# Agentic AI Course: 15 days from first tool call to production agent

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Rahulverma5/agentic-ai-course?quickstart=1)

A hands-on course for building AI agents the way production teams do today. All code runs on the **Gemini API** (official `google-genai` SDK) and works on the free tier. It balances **theory** (how each method evolved, its trade-offs, when to use it) with **practice** (notebooks that run on a free 2-core Codespace) and one **capstone project** that grows every day.

> **Note:** `SYLLABUS.md` is the original all-in-one syllabus and keeps its first code snippets as conceptual references. The day-wise theory notes, notebooks and projects all use Gemini.

## Repository layout

```
agentic-ai-course/
├── SYLLABUS.md                  the complete 15-day syllabus in one file
├── SETUP.md                     Codespaces (free tier) / local / Colab setup
├── week-1/  Foundations         theory/ day-01…07 notes + videos · practice/ day-01…07 notebooks
├── week-2/  Scaling up          theory/ day-08…11 · practice/ day-08…11
├── week-3/  Production          theory/ day-12…15 · practice/ day-12…15
├── projects/
│   ├── file-assistant/          warm-up: the agent loop in ~150 lines
│   └── shopease-support-agent/  capstone: router, tools, RAG, memory, MCP, guardrails, evals, API
├── case-studies/                8 real-world write-ups turned into lessons
├── course_utils/                small helpers the notebooks share (client, cost tracker, agent loop, free providers)
└── .devcontainer/               Codespaces config (installs everything + generates sample data)
```

## Quick start (GitHub Codespaces)
1. Get a free **Gemini API key** at [Google AI Studio](https://aistudio.google.com/apikey), then add it as a Codespaces secret named `GEMINI_API_KEY`: GitHub → Settings → Codespaces → Secrets.
2. Click **Open in GitHub Codespaces** above and choose the **2-core** machine.
3. Open [`week-1/theory/day-01-what-is-an-agent.md`](week-1/theory/day-01-what-is-an-agent.md), then [`week-1/practice/day-01-tokens-and-cost.ipynb`](week-1/practice/day-01-tokens-and-cost.ipynb).

Full instructions, free-tier tips and troubleshooting: **[SETUP.md](SETUP.md)**.

## The 15 days

| Week | Day | Theory | Practice |
|---|---|---|---|
| **1 · Foundations** | 1 | [What an agent is & how we got here](week-1/theory/day-01-what-is-an-agent.md) | [Tokens & cost](week-1/practice/day-01-tokens-and-cost.ipynb) |
| | 2 | [Tool calling & structured outputs](week-1/theory/day-02-tool-calling.md) | [Tool calling](week-1/practice/day-02-tool-calling.ipynb) |
| | 3 | [Agent loop, reasoning & planning](week-1/theory/day-03-agent-loop-and-planning.md) | [Agent loop](week-1/practice/day-03-agent-loop.ipynb) |
| | 4 | [Workflow patterns](week-1/theory/day-04-workflow-patterns.md) | [Workflow patterns](week-1/practice/day-04-workflow-patterns.ipynb) |
| | 5 | [Context engineering & caching](week-1/theory/day-05-context-engineering-and-caching.md) | [Context & caching](week-1/practice/day-05-context-and-caching.ipynb) |
| | 6 | [RAG for agents](week-1/theory/day-06-rag-for-agents.md) | [Hybrid RAG](week-1/practice/day-06-rag.ipynb) |
| | 7 | [Memory](week-1/theory/day-07-memory.md) | [Memory](week-1/practice/day-07-memory.ipynb) |
| **2 · Scaling up** | 8 | [MCP (and A2A)](week-2/theory/day-08-mcp.md) | [MCP server + client](week-2/practice/day-08-mcp.ipynb) |
| | 9 | [Subagents & multi-agent](week-2/theory/day-09-multi-agent-systems.md) | [Single vs multi-agent](week-2/practice/day-09-multi-agent.ipynb) |
| | 10 | [Code-acting & computer-use agents](week-2/theory/day-10-code-and-computer-use-agents.md) | [Data-analysis agent](week-2/practice/day-10-code-agents.ipynb) |
| | 11 | [Evals](week-2/theory/day-11-evals.md) | [Evals & LLM judges](week-2/practice/day-11-evals.ipynb) |
| **3 · Production** | 12 | [Safety & guardrails](week-3/theory/day-12-safety-and-guardrails.md) | [Red-team your agent](week-3/practice/day-12-safety.ipynb) |
| | 13 | [Production engineering](week-3/theory/day-13-production-engineering.md) | [Tracing, retries, cost](week-3/practice/day-13-production.ipynb) |
| | 14 | [Frameworks](week-3/theory/day-14-frameworks.md) | [Same agent, 4 ways](week-3/practice/day-14-frameworks.ipynb) |
| | 15 | [Ship it + what's next](week-3/theory/day-15-ship-it.md) | [Streaming API + final report](week-3/practice/day-15-ship-it.ipynb) |

Each theory note starts with **short videos** (mostly 5–20 min), then explains every subtopic with intuition, math where it helps, a diagram, a code snippet, trade-offs, when to use it, practical lessons and deep-dive links.

## Daily routine (2–3 h)
🎥 videos (15 min) → 📖 theory note (45 min) → 🧪 notebook (45–60 min) → 🏗 capstone milestone (30–45 min) → ✅ checkpoint questions (10 min)

## Projects & case studies
- **[ShopEase Support Agent](projects/shopease-support-agent/)**: a working reference capstone with 16 tests (`python -m pytest`, no key needed) and a 20-case eval suite.
- **[Case studies](case-studies/)**: Anthropic's multi-agent research system, Cognition's single-threaded agents, the Claude Code loop, Contextual Retrieval, code execution with MCP, long-running harnesses, τ-bench, prompt injection.

## License
[MIT](LICENSE)
