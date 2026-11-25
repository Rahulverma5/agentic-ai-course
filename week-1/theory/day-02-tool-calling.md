[← Day 1](../../week-1/theory/day-01-what-is-an-agent.md) · [Week 1 overview](../README.md) · [▶️ Practice notebook](../practice/day-02-tool-calling.ipynb) · [Day 3 →](../../week-1/theory/day-03-agent-loop-and-planning.md)

## Day 2 — Tool calling & structured outputs (the agent's hands)

⏱ 60 min theory · 30 min lab · 60 min capstone

**Goals:** master the function-call protocol, precise schemas, structured output, parallel calls and error handling; learn to *design* tools (the agent–computer interface).


### 🎥 Watch first (short videos)
- 🎥 [Tool Calling Explained: Turn Your LLM into an AI Agent](https://www.youtube.com/watch?v=KJf7SqPCRXg): *community explainer*. the request → run → result cycle
- 🎥 [How LLM Tool Calling Works](https://www.youtube.com/watch?v=QiRdYCNXAxk): *community explainer*. short refresher on the mechanics

> Durations are approximate. "Community explainer" means an independent creator; the written links in each section are the primary sources.

### 2.1 The protocol, precisely

**Intuition.** A function call is a *request form* the model fills in. Your program reads the form, does the work and sends back a *receipt* (`function_response`) that names the same function (and call `id`).

```mermaid
sequenceDiagram
    participant App as Your code
    participant LLM as Model
    App->>LLM: contents + tools[get_order]
    LLM-->>App: functionCall {id: c1, name: get_order, args: {order_id: "O1007"}}
    Note over App: response.function_calls is not empty
    App->>App: run get_order("O1007")
    App->>LLM: functionResponse {id: c1, name: get_order, response: {output: "..."}}
    LLM-->>App: "Your order shipped on..."  (no function calls → done)
```

**Rules that trip everyone up:**
1. Append the model's turn **exactly as received** (`response.candidates[0].content`). With Gemini 3+ models it carries **thought signatures** that must be passed back, or the next request fails validation.
2. Every function call needs a `function_response` with the same name (and `id`), sent in the **next user turn**.
3. If the model makes several calls, return **all responses in one turn**.
4. On failure, return the error as `{"error": "..."}`. Never drop a response.

📖 Deep dive: 📘⭐ [Gemini — Function calling](https://ai.google.dev/gemini-api/docs/generate-content/function-calling) · 📘 [Gemini — Thought signatures](https://ai.google.dev/gemini-api/docs/thought-signatures) · 📘 [Gemini — Tools overview](https://ai.google.dev/gemini-api/docs/tools)

### 2.2 Schemas and structured outputs

**Intuition.** The JSON Schema is the "type signature" the model fills in. A precise schema (types, enums, required fields, patterns) gets you valid arguments almost every time. Still validate them in code. **Structured output** (`response_schema`) constrains the model's *final answer* to your schema.

```python
from google.genai import types

GET_ORDER = types.FunctionDeclaration(
    name="get_order",
    description=("Look up one order by its id (format 'O' + 4 digits, e.g. 'O1007'). "
                 "Returns item, amount, status and dates. Use this before answering any order question."),
    parameters_json_schema={
        "type": "object",
        "properties": {"order_id": {"type": "string", "pattern": "^O\\d{4}$"}},
        "required": ["order_id"],
    },
)
config = types.GenerateContentConfig(tools=[types.Tool(function_declarations=[GET_ORDER])])
```

Structured final output with Pydantic, for example to classify a support ticket:

```python
from pydantic import BaseModel
from typing import Literal

class Ticket(BaseModel):
    category: Literal["order_status", "refund", "warranty", "other"]
    order_id: str | None
    urgency: Literal["low", "medium", "high"]

r = client.models.generate_content(
    model=CHEAP_MODEL, contents="My watch from order O1012 stopped working!! need help asap",
    config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=Ticket))
print(r.parsed)   # Ticket(category='warranty', order_id='O1012', urgency='high')
```

**Trade-offs**

| Approach | Pros | Cons | Use when |
|---|---|---|---|
| Free text + "reply in JSON" prompt (2023 style) | Works everywhere | Breaks sometimes; needs parse/retry | Never, for new code |
| Function call with a precise schema | Valid args almost always | Still validate in code | Arguments to actions |
| Structured output (`response_schema` → `response.parsed`) | Schema-valid final JSON | Some JSON Schema features unsupported | Extraction, classification, routing decisions |

> 💡 **Controlling tool use:** `tool_config=types.ToolConfig(function_calling_config=types.FunctionCallingConfig(mode="ANY"))` forces a function call (`"NONE"` forbids one; `"AUTO"` is the default). When you only want JSON back, prefer structured output over a forced call.

📖 Deep dive: 📘 [Gemini API docs (JSON / structured output section)](https://ai.google.dev/gemini-api/docs)

### 2.3 Parallel tool calls

**Intuition.** If the model needs three independent facts, it can ask for all three at once instead of one per round-trip. That's 3× fewer loop steps.

```python
import concurrent.futures as cf

from course_utils import function_response

calls = response.function_calls or []
with cf.ThreadPoolExecutor() as pool:                      # run independent tools concurrently
    outputs = list(pool.map(lambda fc: run_tool(fc.name, dict(fc.args)), calls))
parts = [function_response(fc, out, is_error=err) for fc, (out, err) in zip(calls, outputs)]
contents.append(response.candidates[0].content)            # model turn as received (thought signatures!)
contents.append(types.Content(role="user", parts=parts))   # ALL responses in ONE turn
```

**Lesson:** splitting parallel results across several messages quietly teaches the model to stop making parallel calls. Always return them together.

### 2.4 Tool design = the agent–computer interface (ACI)

**Intuition.** Tools are a *UI for the model*. A human gets a GUI, and the model gets names, descriptions, schemas and return values. A bad UI confuses a smart user.

**Evolution:** 2023 teams wrapped every REST endpoint as a tool (`GET /users`, `GET /users/{id}/orders`, ...), so models drowned in 50 tools. Today: **fewer, higher-level tools shaped around tasks**.

| ❌ API-shaped | ✅ Task-shaped |
|---|---|
| `list_orders()` returns all 10,000 orders | `search_orders(customer_email, status=None, limit=10)` |
| `get_customer(id)` + `get_orders(id)` + `get_returns(id)` | `get_customer_overview(email)`: profile + 5 recent orders in one call |
| Returns raw JSON with 40 fields and UUIDs | Returns the 6 fields the model needs, with readable names |
| Error: `500` | Error: `"No order O9999. This customer's orders: O1003, O1017"` |

**Principles (from Anthropic's "Writing tools for agents"):**
- **Name and namespace clearly:** `orders_search`, `orders_get`, `refunds_create`.
- **Write descriptions for a new teammate:** what it does, when to use it, input formats, what it returns.
- **Return high-signal, small output.** Paginate or truncate, and give a `response_format="concise"|"detailed"` option.
- **Make errors actionable.** The model reads them and self-corrects.
- **Fewer tools beat more tools.** Overlapping tools cause wrong picks.
- **Test tools with evals.** Read transcripts where the model misused a tool and improve the description.

📖 Deep dive: ⭐ [Anthropic — Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)

### 🧪 Lab → do it in the practice notebook 2 — Tool design A/B test (30 min)
1. Create two versions of an order lookup tool: (A) `get_all_orders()` dumping everything; (B) `search_orders(email, status)`.
2. Ask 5 questions with each version. Record correctness, `prompt_token_count` and number of steps.
3. Break the tool on purpose (raise an exception) and confirm that the `{"error": ...}` response lets the model recover.
4. Repeat with `CHEAP_MODEL` (Flash-Lite). Do smaller models misuse tool A more often?

### 🏗 Capstone — Day 2: `shopease/tools.py`
Implement 4 task-shaped tools over SQLite: `get_customer_overview(email)`, `get_order(order_id)`, `search_orders(email, status)` and `check_refund_eligibility(order_id)`. The last one encodes the 30-day rule in **code**, not in the prompt. Rules that must always hold belong in code. Add precise JSON schemas and actionable error messages, plus unit tests that call each tool directly (no LLM).

### ✅ Checkpoint
1. What happens if you drop the model's turn (with its thought signature) before sending a `function_response`?
2. Why put the refund-eligibility rule in a tool instead of the system prompt?
3. Give two ways a tool's *output* can hurt the agent even when it's correct.
4. When would you use structured outputs instead of a tool call?

---

**Next:** open the [practice notebook](../practice/day-02-tool-calling.ipynb) · capstone milestone in [projects/shopease-support-agent](../../projects/shopease-support-agent/README.md#milestones-build-your-own-version-alongside-the-course)

[← Day 1](../../week-1/theory/day-01-what-is-an-agent.md) · [Week 1 overview](../README.md) · [▶️ Practice notebook](../practice/day-02-tool-calling.ipynb) · [Day 3 →](../../week-1/theory/day-03-agent-loop-and-planning.md)
