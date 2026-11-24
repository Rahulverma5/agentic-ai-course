[← Day 2](../../week-1/theory/day-02-tool-calling.md) · [Week 1 overview](../README.md) · [▶️ Practice notebook](../practice/day-03-agent-loop.ipynb) · [Day 4 →](../../week-1/theory/day-04-workflow-patterns.md)

## Day 3 — The agent loop, reasoning & planning

⏱ 60 min theory · 30 min lab · 60 min capstone

**Goals:** write a production-quality loop from memory; understand stop conditions, budgets, ReAct vs plan-and-execute vs todo lists, and thinking levels.


### 🎥 Watch first (short videos)
- 🎥 [ReAct AI Agents, clearly explained!](https://www.youtube.com/watch?v=vFdIrZyKEwQ): *community explainer*. Thought → Action → Observation
- 🎥 [The Loop Every AI Agent Runs — ReAct Explained](https://www.youtube.com/watch?v=30G13kiyAWs): *community explainer*. walks through the 2022 paper

> Durations are approximate. "Community explainer" means an independent creator; the written links in each section are the primary sources.

### 3.1 The loop: think → act → observe

You built this in `02_agent_loop.py`. Here is the minimal core, with the production guards added:

```python
from google.genai import types
from course_utils import user, to_gemini_tools, function_response

def run_agent(question, tools, system, max_steps=15, max_cost=0.50):
    contents = [user(question)]
    config = types.GenerateContentConfig(system_instruction=system, tools=to_gemini_tools(tools))
    for step in range(max_steps):
        r = client.models.generate_content(model=MODEL, contents=contents, config=config)
        tracker.add(MODEL, r.usage_metadata)
        contents.append(r.candidates[0].content)              # keep it verbatim (thought signatures)

        if not r.function_calls:                              # model decided it's done
            finish = r.candidates[0].finish_reason.name
            return text_of(r) if finish == "STOP" else f"[stopped: {finish}]"   # MAX_TOKENS, SAFETY…
        if tracker.total() > max_cost:                        # budget guard
            return "[stopped: cost budget exceeded]"

        parts = []
        for fc in r.function_calls:
            out, err = run_tool(fc.name, dict(fc.args))
            parts.append(function_response(fc, out, is_error=err))
        contents.append(types.Content(role="user", parts=parts))  # ALL responses in ONE turn
    return "[stopped: step limit]"
```

**How the loop knows what happened** (Gemini)

| Signal | Meaning | What to do |
|---|---|---|
| `response.function_calls` not empty | Wants tools | Run them, send `function_response`s, loop |
| No function calls, `finish_reason == STOP` | Finished | Return the answer |
| `MAX_TOKENS` | Reply cut off | Raise `max_output_tokens` or continue |
| `SAFETY` / `PROHIBITED_CONTENT` / `BLOCKLIST` | Blocked by safety filters | Show a message, log it, don't retry blindly |
| `MALFORMED_FUNCTION_CALL` | The model produced an invalid call | Retry the step; simplify the schema |
| `MISSING_THOUGHT_SIGNATURE` | You didn't pass the model turn back unchanged | Append `candidates[0].content` as received |

**Practical lessons**
- **Always have three budgets:** steps, cost and wall-clock time. Unbounded agents become bills.
- **Log every step** (tool name, args, result size, tokens). You'll turn this into tracing on Day 13.
- The loop stays the same across Google ADK, Claude Code, OpenAI Agents SDK and LangGraph's prebuilt agent. Only the extras differ.

📖 Deep dive: 📘⭐ [Gemini — Function calling (multi-turn and parallel calls)](https://ai.google.dev/gemini-api/docs/generate-content/function-calling) · [How the agent loop works (Claude Agent SDK docs, provider-neutral concepts)](https://code.claude.com/docs/en/agent-sdk/agent-loop)

### 3.2 Planning styles: ReAct vs plan-and-execute vs todo list

```mermaid
flowchart TB
    subgraph ReAct["ReAct: decide one step at a time"]
        r1[Think] --> r2[Act] --> r3[Observe] --> r1
    end
    subgraph PE["Plan-and-Execute: plan everything first"]
        p1[Planner LLM writes full plan] --> p2[Executor runs step 1..n] --> p3[Replan if a step fails]
    end
    subgraph TD["Todo-list (modern hybrid)"]
        t1[Write a todo list with a tool] --> t2[Loop: work on next item] --> t3[Update list: done / new items] --> t2
    end
```

| Style | How | Pros | Cons | Use when |
|---|---|---|---|---|
| **ReAct** | Reason and act each step | Adapts to every observation | Can wander or forget the big picture on long tasks | Short-to-medium tasks (≤ ~15 steps) |
| **Plan-and-Execute** | Plan once, then execute (often with a cheaper model) | Predictable, cheap executor, plan is auditable | Brittle when reality differs from the plan | Well-understood multi-step jobs, report pipelines |
| **Todo list** | ReAct plus a `todo_write` tool the model updates | Keeps the goal visible, replans naturally, the user can see progress | Uses slightly more tokens | Long tasks. Claude Code works this way |

A todo tool is tiny:

```python
TODOS = []
def todo_write(items: list[dict]) -> str:
    """items: [{"task": "...", "status": "pending|in_progress|done"}]. Replaces the whole list."""
    TODOS[:] = items
    return "\n".join(f"[{ {'pending':' ','in_progress':'~','done':'x'}[i['status']] }] {i['task']}" for i in items)
```

**Why it works (intuition):** the model's "working memory" is its context. Rewriting the plan regularly keeps it near the **end** of the context, where attention is strongest (see "lost in the middle", Day 5).

📖 Deep dive: 📄 [ReAct paper](https://arxiv.org/abs/2210.03629) · 📄 [Reflexion — verbal self-reflection (2023)](https://arxiv.org/abs/2303.11366)

### 3.3 Thinking levels and interleaved reasoning

**Intuition.** Modern models can "think" (produce hidden reasoning tokens) before answering, **and between tool calls** (interleaved thinking): *"the search returned nothing → maybe the email has a typo → let me try a partial search."* Reflexion-style self-critique is now built into the model.

**The control knob is `thinking_level`** (`minimal | low | medium | high`; older Gemini 2.5 models used a numeric `thinking_budget` instead):

```python
config = types.GenerateContentConfig(
    tools=to_gemini_tools(TOOLS),
    thinking_config=types.ThinkingConfig(thinking_level="LOW"),   # simple support lookups
)
r = client.models.generate_content(model=MODEL, contents=contents, config=config)
print(r.usage_metadata.thoughts_token_count)   # thinking tokens are billed like output tokens
```

| Thinking level | Cost/latency | Use for |
|---|---|---|
| `minimal` / `low` | Cheapest, fastest | Classification, simple lookups, subagents |
| `medium` | Balanced | Most support/agent turns |
| `high` | Expensive | Hard reasoning, coding, long agentic work |

Not every model supports every level; leave it unset to use the model's default.

**Practical lessons**
- Tune thinking **per route**, not globally. The router (Day 4) can pick the level.
- Less thinking usually means lower latency and fewer thinking tokens; check that tool use stays correct.
- Measure with evals (Day 11) before raising the thinking level "just in case".
- Older pattern: the "think tool" (a no-op tool where the model writes notes). It's useful history, but native interleaved thinking mostly replaces it.

📖 Deep dive: 📘 [Gemini — Thinking](https://ai.google.dev/gemini-api/docs/thinking) · [Anthropic — The "think" tool](https://www.anthropic.com/engineering/claude-think-tool) (history of the idea)

### 3.4 Stopping, looping and getting stuck

Common failure modes and fixes:

| Failure | Symptom | Fix |
|---|---|---|
| Infinite loop | Same tool, same args, again and again | Detect repeats (hash of name + args) and inject "you already tried X" |
| Premature stop | Says "done" without verifying | Prompt: "verify with a tool before finishing", or add a checker step |
| Over-calling | 20 lookups for a 2-step task | Better tool design, clearer instructions |
| Hallucinated tool result | Claims a fact no tool returned | System prompt: "Only state order facts returned by tools", plus a trajectory eval (Day 11) |

```python
from collections import Counter
seen = Counter()
def repeated(fc):                      # call inside the loop for each function call
    key = (fc.name, json.dumps(dict(fc.args), sort_keys=True))
    seen[key] += 1
    return seen[key] >= 3              # third identical call → warn the model / stop
```

### 🧪 Lab → do it in the practice notebook 3 — Planning styles race (30 min)
Give the agent a multi-step task: *"For every gold customer, list undelivered orders and draft one apology email per customer."*
1. Run plain ReAct. 2. Run with a `todo_write` tool. 3. Run plan-and-execute (`MODEL` writes a plan, `CHEAP_MODEL` executes each step).
Compare steps, cost and correctness in a table. Then try `thinking_level` = low vs high.

### 🏗 Capstone — Day 3: `shopease/agent.py`
Wire Day 2's tools into `run_agent` with a ShopEase system prompt (role, tone, "never promise refunds the tools don't confirm", escalation rules). Add step/cost/time budgets and repeat detection. Test it on 10 realistic customer messages and save the transcripts. You'll turn them into evals on Day 11.

### ✅ Checkpoint
1. List the ways a turn can end (function calls, STOP, MAX_TOKENS, SAFETY…) and what your loop does for each.
2. When does plan-and-execute beat ReAct? When does it fail?
3. Why does rewriting a todo list help on long tasks? (Hint: where in the context does it end up?)
4. You lower the thinking level from high to low and accuracy drops 2% while cost drops 60%. How do you decide?

---

**Next:** open the [practice notebook](../practice/day-03-agent-loop.ipynb) · capstone milestone in [projects/shopease-support-agent](../../projects/shopease-support-agent/README.md#milestones-build-your-own-version-alongside-the-course)

[← Day 2](../../week-1/theory/day-02-tool-calling.md) · [Week 1 overview](../README.md) · [▶️ Practice notebook](../practice/day-03-agent-loop.ipynb) · [Day 4 →](../../week-1/theory/day-04-workflow-patterns.md)
