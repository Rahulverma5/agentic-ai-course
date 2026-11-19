# Agentic AI Course: 15 days from first tool call to production agent

A hands-on course for building AI agents the way production teams do today, with theory, history, trade-offs and code for every topic.

- 📚 **[SYLLABUS.md](SYLLABUS.md)**: the full 15-day plan (2–3 h/day). Each subtopic has an intuitive explanation, the math where it helps, Mermaid diagrams, a small code example, trade-offs, when to use it, and verified deep-dive links (Anthropic, OpenAI, Cognition, LangChain, papers, videos).
- 🏗 **Capstone:** the *ShopEase Support Agent* grows every day: tools, router, RAG, memory, MCP, subagents, evals, guardrails, tracing, cost optimization and a streaming API.
- 🧪 **Labs:** designed for Google Colab or Kaggle. Code uses the Claude API, and a small adapter lets every lab run on free Gemini or Groq tiers too.

## What's in this repo

| Path | What it is |
|---|---|
| `SYLLABUS.md` | The course: 3 weeks covering foundations, scaling up and production |
| `01_tool_call.py` | Warm-up 1: one tool call by hand. The model asks, your code runs it, you send the result back |
| `02_agent_loop.py` | Warm-up 2: a ~150-line file-assistant agent with the core `while` loop, parallel tool calls, errors as feedback, step limit and sandboxed paths |
| `workspace/` | Sample files the warm-up agent works on |

## Quick start

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."   # from https://platform.claude.com
python 01_tool_call.py
python 02_agent_loop.py               # try: "Read todo.txt and create plan.md sorted by priority"
```

Then open [SYLLABUS.md](SYLLABUS.md) and start Day 1.

## Course map

| Week | Days |
|---|---|
| 1: Foundations | What agents are and how they evolved · Tool calling · The agent loop and planning · Workflow patterns · Context engineering and caching · RAG · Memory |
| 2: Scaling up | MCP and A2A · Subagents and multi-agent systems · Code-writing and computer-use agents · Evals |
| 3: Production | Safety and guardrails · Reliability, cost and latency · Frameworks (Claude Agent SDK, OpenAI Agents SDK, LangGraph) · Shipping it and what's next |

## License

[MIT](LICENSE)
