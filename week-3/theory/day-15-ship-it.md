[← Day 14](../../week-3/theory/day-14-frameworks.md) · [Week 3 overview](../README.md) · [▶️ Practice notebook](../practice/day-15-ship-it.ipynb)

## Day 15 — Ship it: API, launch checklist, and what's next

⏱ 30 min theory · 90 min ship · 30 min reflection

**Goals:** expose the agent as a streaming API, produce a final eval report, run through a production readiness checklist, and map the frontier.


### 🎥 Watch first (short videos)
- 🎥 [Andrej Karpathy: Software Is Changing (Again) (optional, ~39 min)](https://www.youtube.com/watch?v=LCEmiRjPEtQ): *Y Combinator AI Startup School*. Software 3.0 and building for agents
- 🎥 [From Context Engineering to AI Agent Harnesses (optional)](https://www.youtube.com/watch?v=2Muxy3wE-E0): *Lance Martin (LangChain)*. where long-running agents are heading

> Durations are approximate. "Community explainer" means an independent creator; the written links in each section are the primary sources.

### 15.1 Streaming API with FastAPI

```python
# app.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google import genai
from google.genai import types

app, client = FastAPI(), genai.Client()   # reads GEMINI_API_KEY

class ChatIn(BaseModel):
    conversation_id: str
    message: str

@app.post("/chat")
def chat(body: ChatIn):
    contents = load_history(body.conversation_id) + [
        types.Content(role="user", parts=[types.Part.from_text(text=body.message)])]
    def events():
        for chunk in run_agent_streaming(contents):          # yields text deltas and status lines
            yield f"data: {chunk}\n\n"                       # Server-Sent Events
        save_history(body.conversation_id, contents)
    return StreamingResponse(events(), media_type="text/event-stream")
```

Inside `run_agent_streaming`, stream each model turn and yield status lines during tools:

```python
CONFIG = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, tools=to_gemini_tools(TOOLS))

def run_agent_streaming(contents):
    for _ in range(MAX_STEPS):
        parts = []
        for chunk in client.models.generate_content_stream(model=MODEL, contents=contents, config=CONFIG):
            for p in chunk.candidates[0].content.parts or []:
                parts.append(p)                              # keep every part (thought signatures!)
                if p.text and not p.thought:
                    yield p.text
        contents.append(types.Content(role="model", parts=parts))
        calls = [p.function_call for p in parts if p.function_call]
        if not calls:
            return
        responses = []
        for fc in calls:
            yield f"[checking: {fc.name}]"
            out, err = run_tool(fc.name, dict(fc.args))
            responses.append(function_response(fc, out, is_error=err))
        contents.append(types.Content(role="user", parts=responses))
```

Run it in Codespaces with `uvicorn` (port 8000 is forwarded) or in a notebook background thread, test with `httpx`, or deploy for free on a small container platform. Store history in SQLite/Redis keyed by `conversation_id`, never in process memory, so the API scales and survives restarts.

### 15.2 Production readiness checklist

| Area | ✅ Ready when |
|---|---|
| **Scope** | Clear list of what the agent does and refuses; human escalation path exists |
| **Evals** | Suite of ≥50 cases incl. adversarial; CI gate; pass^k tracked; judge calibrated |
| **Safety** | Auth in code, least-privilege tools, approval on risky actions, PII handling, red-team results logged |
| **Reliability** | Budgets (steps/cost/time), retries + backoff, idempotency, fallbacks, graceful error messages |
| **Observability** | Traces for every run, cost/latency dashboards, alerts on error rate and spend |
| **Cost** | Caching verified (hit rate), routing in place, cost per resolved conversation known |
| **Data** | Retention policy, memory write policy, deletion on request |
| **Ops** | Prompt/tool versions tracked, rollback plan, shadow/canary rollout, feedback loop from real failures → eval cases |

### 15.3 Long-running agents (where the frontier is)

**Harnesses for long work.** Tasks that last hours exceed one context window. Anthropic's long-running harness pattern:
- An **initializer** session sets up the environment: a feature list, a progress file and git.
- Each new **coding** session reads the progress, does one increment, tests it, commits and updates the notes. That is memory + context engineering + evals combined.
- Structured state (JSON feature lists) was edited more reliably than free-form markdown.

Other directions to follow:
- **RL-trained agents:** models trained with reinforcement learning on real tool-use environments. This is why each model generation needs *less* scaffolding.
- **Benchmarks to watch:** SWE-bench Verified (coding), τ-bench (tool + user interaction, pass^k), OSWorld (computer use). Read leaderboards skeptically, since setups differ and some benchmarks get saturated or gamed.
- **Skills and progressive disclosure:** packaging procedural knowledge as loadable folders instead of giant prompts.

📖 Deep dive: ⭐ [Anthropic — Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) · [SWE-bench](https://www.swebench.com/) · 🧑‍💻 [Kaggle × Google — 5-Day AI Agents course (free notebooks + whitepapers)](https://www.kaggle.com/learn-guide/5-day-agents) · [Claude Code best practices](https://code.claude.com/docs/en/best-practices)

### 🏗 Capstone — Day 15 (final)
1. Ship `app.py` with streaming and persisted history.
2. Run the full eval suite 3× and publish `report.md` (pass rate, pass^3, cost per conversation, p50/p95 latency, safety results).
3. Write a **one-page design doc**: architecture diagram, key decisions (router, single writer, approval gate, caching), known limitations, next steps. This becomes your portfolio piece and interview story.

### ✅ Final self-assessment
Can you, without notes:
1. Write an agent loop with budgets and error handling?
2. Decide workflow vs agent for a new problem and defend the choice?
3. Explain and implement caching, context trimming and compaction?
4. Build hybrid RAG and measure recall@k?
5. Design an eval suite with calibrated judges and explain pass^k?
6. Analyze an agent with the lethal trifecta and add the right controls?
7. Cut cost 50%+ while showing that quality held?

---

**Next:** open the [practice notebook](../practice/day-15-ship-it.ipynb) · capstone milestone in [projects/shopease-support-agent](../../projects/shopease-support-agent/README.md#milestones-build-your-own-version-alongside-the-course)

[← Day 14](../../week-3/theory/day-14-frameworks.md) · [Week 3 overview](../README.md) · [▶️ Practice notebook](../practice/day-15-ship-it.ipynb)
