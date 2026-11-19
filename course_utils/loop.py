"""Reference agent loop (the one you build by hand on Day 3), reused in later notebooks."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Callable

from .cost import tracker
from .llm import MODEL, get_client


@dataclass
class AgentResult:
    text: str
    stop_reason: str
    steps: int
    tool_calls: list = field(default_factory=list)  # [(name, input, is_error)]
    seconds: float = 0.0


def make_tool_result(tool_use_id: str, content: str, is_error: bool = False) -> dict:
    return {"type": "tool_result", "tool_use_id": tool_use_id, "content": content, "is_error": is_error}


def _run_tool(functions: dict[str, Callable], name: str, args: dict) -> tuple[str, bool]:
    if name not in functions:
        return f"Error: unknown tool '{name}'. Available: {', '.join(functions)}", True
    try:
        out = functions[name](**args)
        return (out if isinstance(out, str) else json.dumps(out, default=str)), False
    except Exception as e:  # errors go back to the model, they don't crash the loop
        return f"Error: {type(e).__name__}: {e}", True


def run_agent(messages: list, tools: list[dict], functions: dict[str, Callable], system: str = "",
              model: str = MODEL, max_steps: int = 15, max_cost: float = 1.0, max_seconds: float = 300,
              effort: str | None = None, max_tokens: int = 16000, verbose: bool = True,
              client=None, on_tool: Callable | None = None, **create_kwargs) -> AgentResult:
    """Think → act → observe until the model stops, or a budget is hit.

    `messages` is modified in place, so you can keep chatting with the same list.
    `on_tool(name, args)` can return a string to *replace* running the tool (e.g. "declined by human").
    """
    client = client or get_client()
    start, cost_at_start, calls = time.time(), tracker.total(), []
    params = dict(model=model, max_tokens=max_tokens, tools=tools, **create_kwargs)
    if system:
        params["system"] = system
    if effort:
        params["output_config"] = {"effort": effort}

    for step in range(1, max_steps + 1):
        r = client.messages.create(messages=messages, **params)
        tracker.add(model, r.usage, label=f"agent step {step}")
        messages.append({"role": "assistant", "content": r.content})
        text = "".join(b.text for b in r.content if b.type == "text")
        if verbose and text.strip():
            print(f"🤖 {text.strip()}")

        if r.stop_reason != "tool_use":  # end_turn, max_tokens, refusal, ...
            return AgentResult(text, r.stop_reason, step, calls, time.time() - start)

        results = []
        for b in r.content:
            if b.type != "tool_use":
                continue
            override = on_tool(b.name, b.input) if on_tool else None
            out, err = (override, False) if isinstance(override, str) else _run_tool(functions, b.name, b.input)
            calls.append((b.name, b.input, err))
            if verbose:
                print(f"   🔧 {b.name}({json.dumps(b.input)[:90]}) → {out[:80]!r}{' ❌' if err else ''}")
            results.append(make_tool_result(b.id, out, err))
        messages.append({"role": "user", "content": results})

        if tracker.total() - cost_at_start > max_cost:
            return AgentResult("[stopped: cost budget]", "budget", step, calls, time.time() - start)
        if time.time() - start > max_seconds:
            return AgentResult("[stopped: time budget]", "budget", step, calls, time.time() - start)

    return AgentResult("[stopped: step limit]", "step_limit", max_steps, calls, time.time() - start)
