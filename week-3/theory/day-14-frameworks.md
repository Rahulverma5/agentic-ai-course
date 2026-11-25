[← Day 13](../../week-3/theory/day-13-production-engineering.md) · [Week 3 overview](../README.md) · [▶️ Practice notebook](../practice/day-14-frameworks.ipynb) · [Day 15 →](../../week-3/theory/day-15-ship-it.md)

## Day 14 — Frameworks: what they give you and what they hide

⏱ 45 min theory · 105 min hands-on (rebuild + compare)

**Goals:** rebuild the capstone's core (agent + 2 tools) in three frameworks, compare them honestly, and know when to pick each one or none.


### 🎥 Watch first (short videos)
- 🎥 [Agentic AI Frameworks Explained: Workflows, Multi-Agent, & Production](https://www.youtube.com/watch?v=ZVPlLaehjLk): *IBM Technology*. LangChain, AutoGen, CrewAI compared

> Durations are approximate. "Community explainer" means an independent creator; the written links in each section are the primary sources.

### 14.1 The landscape

| Layer | What it is | Examples |
|---|---|---|
| **Raw SDK** | You write the loop | `google-genai` (what you've done for 13 days), OpenAI / Anthropic SDKs |
| **Loop helpers** | SDK runs the loop over your tools | google-genai **automatic function calling** (pass Python functions as tools) |
| **Agent frameworks** | Abstractions: agents, tools, handoffs, guardrails, sessions | **Google ADK**, OpenAI Agents SDK, Pydantic AI, CrewAI |
| **Agent harnesses** | Batteries included: file/bash tools, context management, subagents, permissions | Gemini CLI, Claude Agent SDK (coding/ops agents) |
| **Orchestration runtimes** | Graphs/state machines with persistence, retries, human-in-the-loop | **LangGraph** |

### 14.2 Same agent, four ways (all on Gemini)

```python
def get_order(order_id: str) -> str:
    """Look up a ShopEase order by id, e.g. 'O1007'."""
    return lookup_order(order_id)
```

**google-genai automatic function calling**: the loop disappears, the tools stay. The SDK turns the function's signature and docstring into a declaration, calls it, and loops:

```python
r = client.models.generate_content(model=MODEL, contents="Where is O1007?",
    config=types.GenerateContentConfig(tools=[get_order]))   # a Python function, not a declaration
print(r.text)                                   # r.automatic_function_calling_history shows each step
```

**Google ADK (Agent Development Kit)**: Google's framework for agents: tools, sessions/state, multi-agent (sub-agents), callbacks, evaluation and deployment:

```python
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner

agent = Agent(name="shopease_support", model=MODEL, instruction="You are ShopEase support.", tools=[get_order])
runner = InMemoryRunner(agent=agent, app_name="shopease")
session = await runner.session_service.create_session(app_name="shopease", user_id="u1")
async for event in runner.run_async(user_id="u1", session_id=session.id,
                                    new_message=types.Content(role="user", parts=[types.Part(text="Where is O1007?")])):
    if event.is_final_response():
        print(event.content.parts[0].text)
```

**OpenAI Agents SDK**: agents, tools, handoffs, guardrails, sessions and tracing; Gemini plugs in through its LiteLLM extension:

```python
from agents import Agent, Runner, function_tool
from agents.extensions.models.litellm_model import LitellmModel

support = Agent(name="ShopEase support", instructions="Help customers with orders.", tools=[function_tool(get_order)],
                model=LitellmModel(model="gemini/gemini-flash-latest", api_key=os.environ["GEMINI_API_KEY"]))
result = await Runner.run(support, "Where is O1007?")
print(result.final_output)
```

**LangGraph**: the loop as an explicit graph (state → nodes → edges), with persistence and interrupts:

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

tools = [tool(get_order)]
llm = ChatGoogleGenerativeAI(model=MODEL, google_api_key=os.environ["GEMINI_API_KEY"]).bind_tools(tools)
def agent(state: MessagesState): return {"messages": [llm.invoke(state["messages"])]}

g = StateGraph(MessagesState)
g.add_node("agent", agent); g.add_node("tools", ToolNode(tools))
g.add_edge(START, "agent"); g.add_conditional_edges("agent", tools_condition); g.add_edge("tools", "agent")
app = g.compile()
print(app.invoke({"messages": [("user", "Where is O1007?")]})["messages"][-1].content)
```

> ⚠️ Frameworks move fast. Pin versions (`pip install x==...`) in notebooks and check the quickstart if an import has moved.

You'll notice the LangGraph graph **is** your `while` loop drawn as nodes: `agent → (tool calls?) → tools → agent → END`.

### 14.3 Honest comparison

| | Raw SDK (yours) | Automatic function calling | Google ADK | OpenAI Agents SDK | LangGraph |
|---|---|---|---|---|---|
| Control / transparency | ✅✅ Full | Medium (hidden loop) | Medium | Medium | ✅ High (explicit graph) |
| Built-in tools | Gemini built-ins (search, code execution) | Same | ✅ Built-ins + MCP + OpenAPI tools | Some (hosted tools) | Via integrations |
| Multi-agent / handoffs | DIY | ❌ | ✅ Sub-agents, workflow agents | ✅ Handoffs | ✅ Any topology |
| Persistence, resume, human-in-the-loop | DIY | ❌ | Sessions, state, callbacks | Sessions | ✅✅ Checkpointing, interrupts |
| Tracing / evals | DIY / OTel | ❌ | Built-in dev UI (`adk web`), eval tooling | ✅ Built-in tracing | LangSmith / OTel |
| Lock-in | None | Gemini | Gemini-first (other models via LiteLLM) | Lightly OpenAI-leaning | Provider-neutral |
| Best for | Learning, custom products, tight control | Quick scripts, simple tool use | Gemini-based production agents, multi-agent apps | Multi-agent apps with handoffs/guardrails | Long-running, stateful, auditable workflows |

**Practical lessons**
- **Frameworks don't fix bad tools or bad context.** The hard 80% (tool design, context, evals, safety) is the same everywhere. That's why you learned it first.
- Choose a framework for **operational features** you'd otherwise build: persistence, resume after crash, human-in-the-loop, tracing, deployment.
- If you can't explain what the framework sends to the model, debug with raw logs first.

📖 Deep dive: 📘⭐ [Google ADK — Python quickstart](https://adk.dev/get-started/python/) · 📘 [Gemini — Function calling (incl. automatic calling)](https://ai.google.dev/gemini-api/docs/generate-content/function-calling) · 📘 [OpenAI Agents SDK (GitHub)](https://github.com/openai/openai-agents-python) · 📘 [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) · [LangChain — How to think about agent frameworks](https://www.langchain.com/blog/how-to-think-about-agent-frameworks)

### 🧪 Lab → do it in the practice notebook + 🏗 Capstone — Day 14
Rebuild the ShopEase core (router + agent + `get_order` + `check_refund_eligibility`) in LangGraph and one other framework. Run **the same Day 11 eval suite** on all versions and fill in a comparison table: pass rate, cost, latency, lines of code, debugging experience. Write a one-page "framework decision record" (ADR), the way you would at a company.

### ✅ Checkpoint
1. What does LangGraph give you that your loop doesn't?
2. When would you choose Google ADK over the raw `google-genai` SDK?
3. Why did learning from scratch first make framework debugging easier?
4. Name 2 signs you should drop a framework.

---

**Next:** open the [practice notebook](../practice/day-14-frameworks.ipynb) · capstone milestone in [projects/shopease-support-agent](../../projects/shopease-support-agent/README.md#milestones-build-your-own-version-alongside-the-course)

[← Day 13](../../week-3/theory/day-13-production-engineering.md) · [Week 3 overview](../README.md) · [▶️ Practice notebook](../practice/day-14-frameworks.ipynb) · [Day 15 →](../../week-3/theory/day-15-ship-it.md)
