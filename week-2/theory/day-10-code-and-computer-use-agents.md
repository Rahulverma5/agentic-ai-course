[← Day 9](../../week-2/theory/day-09-multi-agent-systems.md) · [Week 2 overview](../README.md) · [▶️ Practice notebook](../practice/day-10-code-agents.ipynb) · [Day 11 →](../../week-2/theory/day-11-evals.md)

## Day 10 — Code-acting agents, sandboxes & computer use

⏱ 60 min theory · 45 min lab · 30 min capstone

**Goals:** understand why "code as action" is so powerful, run model-written code safely, and know where computer-use agents fit.


### 🎥 Watch first (short videos)
- 🎥 [Claude NEW Computer Use in 6 Minutes](https://www.youtube.com/watch?v=ZUBJqLGKoZI): *community explainer*. what screenshot → click loops look like
- 🎥 [Agent Harness explained in 11 minutes](https://www.youtube.com/watch?v=Qc1uWZW8gF8): *community explainer*. bash + files as the universal tool

> Durations are approximate. "Community explainer" means an independent creator; the written links in each section are the primary sources.

### 10.1 CodeAct: actions as code instead of JSON

**Intuition.** With JSON tools, "average order value per tier" takes many round-trips (get customers → get orders → ...). With code, the model writes **one script** with loops, variables and math, and gets one result back.

```python
# JSON-tool style: ~N tool calls, each result passes through the context
# Code style: ONE action, the data never enters the context
code = """
import sqlite3, statistics
db = sqlite3.connect('shopease/data/shopease.db')
rows = db.execute('SELECT c.tier, o.amount FROM orders o JOIN customers c ON c.id=o.customer_id').fetchall()
by_tier = {}
for tier, amt in rows: by_tier.setdefault(tier, []).append(amt)
print({t: round(statistics.mean(v), 2) for t, v in by_tier.items()})
"""
```

The CodeAct paper reported higher success rates with fewer actions than JSON/text actions. "Bash + files" is why coding agents are so capable: one tool gives access to thousands of programs.

| | JSON tools | Code actions |
|---|---|---|
| Safety | ✅ Easy to constrain | ⚠️ Needs a sandbox |
| Composability (loops, filters) | ❌ Poor | ✅ Excellent |
| Data-heavy tasks | ❌ Floods context | ✅ Data stays in the sandbox |
| Predictability | ✅ | ⚠️ |
| Use for | Business actions (refunds, emails) | Analysis, transformation, coding |

📖 Deep dive: 📄 [CodeAct — Executable Code Actions Elicit Better LLM Agents (2024)](https://arxiv.org/abs/2402.01030)

### 10.2 Running model-written code safely

**Never `exec()` model code in your main process.** The levels of isolation:

| Level | Example | Safety | Use |
|---|---|---|---|
| ❌ `exec()` in-process | — | None | Never |
| Subprocess + timeout | `subprocess.run([...], timeout=10)` | Low (same machine, same files) | Notebooks/learning only |
| Container | Docker with no network, read-only mounts, CPU/mem limits | Good | Self-hosted production |
| Managed sandbox | Provider code-execution tool, hosted sandboxes | Good, zero ops | Most teams |

Learning-only runner (Colab):

```python
import subprocess, tempfile, sys
def run_python(code: str) -> str:
    """LEARNING ONLY: runs code in a subprocess with a timeout. Not a security boundary."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
    try:
        p = subprocess.run([sys.executable, f.name], capture_output=True, text=True, timeout=10)
        return (p.stdout + p.stderr)[-4000:]          # truncate output (context hygiene)
    except subprocess.TimeoutExpired:
        return "Error: timed out after 10s"
```

Hosted alternative, Gemini's built-in **code execution tool** (Google runs the sandbox):

```python
r = client.models.generate_content(
    model=MODEL, contents="Simulate 10,000 dice rolls and give the mean and a histogram summary.",
    config=types.GenerateContentConfig(tools=[types.Tool(code_execution=types.ToolCodeExecution())]))
for p in r.candidates[0].content.parts:
    if p.executable_code:       print("code:", p.executable_code.code)
    if p.code_execution_result: print("result:", p.code_execution_result.output)
```

**Programmatic tool calling:** the model writes code *inside* the code-execution sandbox that calls **your** tools. Many tool calls run without each result passing through the context, which is the same idea as 8.4.

📖 Deep dive: 📘 [Gemini — Tools overview (code execution, search, URL context)](https://ai.google.dev/gemini-api/docs/tools)

### 10.3 Computer-use and browser agents (overview)

**Intuition:** when there's no API, the agent uses the GUI. It takes a screenshot, decides where to click or what to type, takes another screenshot, and repeats. It's the same loop with "screen" tools.

| Pros | Cons |
|---|---|
| Works with any app or website, including legacy systems | Slow (a screenshot per step), expensive, more fragile |
| No integration work | Bigger prompt-injection surface (any web page can carry instructions) |

**Rule:** API > CLI > browser automation (Playwright scripts) > computer use. Use computer use only when nothing above it is available. Benchmarks such as OSWorld track progress.

📖 Deep dive: 📘 [Gemini — Tools overview (incl. computer use)](https://ai.google.dev/gemini-api/docs/tools) · [OSWorld benchmark](https://os-world.github.io/)

### 🧪 Lab → do it in the practice notebook 10 — Data-analysis agent (45 min)
Give an agent a single `run_python` tool plus a CSV export of the orders table (add 500 synthetic rows). Ask 5 analytics questions ("refund rate by item", "plot monthly revenue", ...). Compare against an agent with only JSON tools (`get_order`, `search_orders`) on the same questions: steps, tokens, correctness. Then try the hosted code-execution tool.

### 🏗 Capstone — Day 10
Add an internal **"ops analytics" mode**: support managers can ask data questions. Route those to a code-acting agent with **read-only** DB access (open SQLite in `mode=ro`) and the subprocess sandbox, never to customers.

### ✅ Checkpoint
1. Why do code actions use less context on data-heavy tasks?
2. Rank 4 isolation levels from least to most safe.
3. When is computer use the right choice?
4. What's programmatic tool calling and which problem does it solve?

---

**Next:** open the [practice notebook](../practice/day-10-code-agents.ipynb) · capstone milestone in [projects/shopease-support-agent](../../projects/shopease-support-agent/README.md#milestones-build-your-own-version-alongside-the-course)

[← Day 9](../../week-2/theory/day-09-multi-agent-systems.md) · [Week 2 overview](../README.md) · [▶️ Practice notebook](../practice/day-10-code-agents.ipynb) · [Day 11 →](../../week-2/theory/day-11-evals.md)
