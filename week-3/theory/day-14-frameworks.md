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
| **Raw SDK** | You write the loop | Anthropic / OpenAI SDKs (what you've done for 13 days) |
| **Loop helpers** | SDK runs the loop over your tools | Anthropic Tool Runner (`@beta_tool`) |
| **Agent frameworks** | Abstractions: agents, tools, handoffs, guardrails | OpenAI Agents SDK, Pydantic AI, CrewAI |
| **Agent harnesses** | Batteries included: file/bash tools, context management, subagents, permissions | **Claude Agent SDK** (Claude Code as a library) |
| **Orchestration runtimes** | Graphs/state machines with persistence, retries, human-in-the-loop | **LangGraph** |

### 14.2 Same agent, three ways (plus the SDK helper)

**Anthropic Tool Runner**: the loop disappears, the tools stay:

```python
from anthropic import beta_tool
@beta_tool
def get_order(order_id: str) -> str:
    """Look up a ShopEase order by id, e.g. 'O1007'."""
    return lookup_order(order_id)

runner = client.beta.messages.tool_runner(model=MODEL, max_tokens=16000, tools=[get_order],
                                          messages=[{"role": "user", "content": "Where is O1007?"}])
for message in runner: pass          # each iteration = one model turn; stops when done
print(message.content[-1].text)
```

**Claude Agent SDK**: a full harness with built-in tools, hooks, subagents and permissions. Custom tools are exposed as an in-process MCP server:

```python
from claude_agent_sdk import query, ClaudeAgentOptions, tool, create_sdk_mcp_server

@tool("get_order", "Look up a ShopEase order by id", {"order_id": str})
async def get_order(args):
    return {"content": [{"type": "text", "text": lookup_order(args["order_id"])}]}

server = create_sdk_mcp_server(name="shopease", version="1.0.0", tools=[get_order])
options = ClaudeAgentOptions(system_prompt="You are ShopEase support.",
                             mcp_servers={"shopease": server},
                             allowed_tools=["mcp__shopease__get_order"])
async for msg in query(prompt="Where is O1007?", options=options):
    print(msg)
```

**OpenAI Agents SDK**: agents, tools, handoffs, guardrails, sessions and tracing built in:

```python
from agents import Agent, Runner, function_tool

@function_tool
def get_order(order_id: str) -> str:
    """Look up a ShopEase order by id."""
    return lookup_order(order_id)

support = Agent(name="ShopEase support", instructions="Help customers with orders.", tools=[get_order])
result = Runner.run_sync(support, "Where is O1007?")
print(result.final_output)
# Non-OpenAI models (Claude, Gemini) can be plugged in through its LiteLLM model extension.
```

**LangGraph**: the loop as an explicit graph (state → nodes → edges), with persistence and interrupts:

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

@tool
def get_order(order_id: str) -> str:
    """Look up a ShopEase order by id."""
    return lookup_order(order_id)

llm = ChatAnthropic(model=MODEL).bind_tools([get_order])
def agent(state: MessagesState): return {"messages": [llm.invoke(state["messages"])]}

g = StateGraph(MessagesState)
g.add_node("agent", agent); g.add_node("tools", ToolNode([get_order]))
g.add_edge(START, "agent"); g.add_conditional_edges("agent", tools_condition); g.add_edge("tools", "agent")
app = g.compile()
print(app.invoke({"messages": [("user", "Where is O1007?")]})["messages"][-1].content)
```

> ⚠️ Frameworks move fast. Pin versions (`pip install x==...`) in notebooks and check the quickstart if an import has moved.

You'll notice the LangGraph graph **is** your `while` loop drawn as nodes: `agent → (tool calls?) → tools → agent → END`.

### 14.3 Honest comparison

| | Raw SDK (yours) | Claude Agent SDK | OpenAI Agents SDK | LangGraph |
|---|---|---|---|---|
| Control / transparency | ✅✅ Full | Medium | Medium | ✅ High (explicit graph) |
| Built-in tools (files, bash, web) | ❌ | ✅✅ | Some (hosted tools) | Via integrations |
| Multi-agent / handoffs | DIY | Subagents | ✅ Handoffs | ✅ Any topology |
| Persistence, resume, human-in-the-loop | DIY | Sessions, hooks, permissions | Sessions | ✅✅ Checkpointing, interrupts |
| Tracing | DIY / OTel | Built in | ✅ Built in | LangSmith / OTel |
| Lock-in | None | Claude models | Lightly OpenAI-leaning | Provider-neutral |
| Best for | Learning, custom products, tight control | Coding/file/ops agents fast | Multi-agent apps with handoffs/guardrails | Long-running, stateful, auditable workflows |

**Practical lessons**
- **Frameworks don't fix bad tools or bad context.** The hard 80% (tool design, context, evals, safety) is the same everywhere. That's why you learned it first.
- Choose a framework for **operational features** you'd otherwise build: persistence, resume after crash, human-in-the-loop, tracing.
- If you can't explain what the framework sends to the model, debug with raw logs first.

📖 Deep dive: 📘⭐ [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview) · [Anthropic — Building agents with the Claude Agent SDK](https://claude.com/blog/building-agents-with-the-claude-agent-sdk) · 📘 [OpenAI Agents SDK (GitHub)](https://github.com/openai/openai-agents-python) · 📘 [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) · [LangChain — How to think about agent frameworks](https://www.langchain.com/blog/how-to-think-about-agent-frameworks)

### 🧪 Lab → do it in the practice notebook + 🏗 Capstone — Day 14
Rebuild the ShopEase core (router + agent + `get_order` + `check_refund_eligibility`) in LangGraph and one other framework. Run **the same Day 11 eval suite** on all versions and fill in a comparison table: pass rate, cost, latency, lines of code, debugging experience. Write a one-page "framework decision record" (ADR), the way you would at a company.

### ✅ Checkpoint
1. What does LangGraph give you that your loop doesn't?
2. When would you choose the Claude Agent SDK over the raw API?
3. Why did learning from scratch first make framework debugging easier?
4. Name 2 signs you should drop a framework.

---

**Next:** open the [practice notebook](../practice/day-14-frameworks.ipynb) · capstone milestone in [projects/shopease-support-agent](../../projects/shopease-support-agent/README.md#milestones-build-your-own-version-alongside-the-course)

[← Day 13](../../week-3/theory/day-13-production-engineering.md) · [Week 3 overview](../README.md) · [▶️ Practice notebook](../practice/day-14-frameworks.ipynb) · [Day 15 →](../../week-3/theory/day-15-ship-it.md)
