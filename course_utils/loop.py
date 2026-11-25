"""Reference agent loop for Gemini (the one you build by hand on Day 3), reused in later notebooks."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Callable

from .cost import tracker
from . import llm
from .llm import get_client, text_of, thinking


@dataclass
class AgentResult:
    text: str
    stop_reason: str
    steps: int
    tool_calls: list = field(default_factory=list)  # [(name, args, is_error)]
    seconds: float = 0.0


def to_gemini_tools(tools: list[dict]):
    """Course tool format {name, description, input_schema} → one Gemini Tool with FunctionDeclarations.

    The schemas are plain JSON Schema, so the same definitions work across providers.
    """
    from google.genai import types

    decls = [types.FunctionDeclaration(
        name=t["name"], description=t.get("description", ""),
        parameters_json_schema=t.get("input_schema") or {"type": "object", "properties": {}})
        for t in tools]
    return [types.Tool(function_declarations=decls)]


def function_response(call, output: str, is_error: bool = False):
    """The reply to one function call, matched by name and id."""
    from google.genai import types

    return types.Part(function_response=types.FunctionResponse(
        id=call.id, name=call.name, response={"error": output} if is_error else {"output": output}))


def _run_tool(functions: dict[str, Callable], name: str, args: dict) -> tuple[str, bool]:
    if name not in functions:
        return f"Error: unknown tool '{name}'. Available: {', '.join(functions)}", True
    try:
        out = functions[name](**(args or {}))
        return (out if isinstance(out, str) else json.dumps(out, default=str)), False
    except Exception as e:  # errors go back to the model, they don't crash the loop
        return f"Error: {type(e).__name__}: {e}", True


def run_agent(contents, tools: list[dict], functions: dict[str, Callable], system: str = "",
              model: str | None = None, max_steps: int = 15, max_cost: float = 1.0, max_seconds: float = 300,
              thinking_level: str | None = None, verbose: bool = True, client=None,
              on_tool: Callable | None = None, **config) -> AgentResult:
    """Think → act → observe until the model stops calling tools, or a budget is hit.

    `contents` is a prompt string or a list of Content objects; a list is modified in place so you
    can keep chatting. `on_tool(name, args)` may return a string to *replace* running the tool.
    """
    from google.genai import types

    client = client or get_client()
    model = model or llm.MODEL  # looked up at call time (check_setup may have switched it)
    if isinstance(contents, str):
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=contents)])]
    cfg = types.GenerateContentConfig(system_instruction=system or None, tools=to_gemini_tools(tools) if tools else None,
                                      thinking_config=thinking(thinking_level), **config)
    start, cost_at_start, calls = time.time(), tracker.total(), []

    for step in range(1, max_steps + 1):
        r = client.models.generate_content(model=model, contents=contents, config=cfg)
        tracker.add(model, r.usage_metadata, label=f"agent step {step}")
        candidate = r.candidates[0] if r.candidates else None
        if candidate and candidate.content:
            contents.append(candidate.content)  # keep it verbatim: includes thought signatures
        text = text_of(r)
        if verbose and text.strip():
            print(f"🤖 {text.strip()}")

        fcs = r.function_calls or []
        if not fcs:  # STOP, MAX_TOKENS, SAFETY, ...
            reason = candidate.finish_reason.name if candidate and candidate.finish_reason else "STOP"
            return AgentResult(text, reason, step, calls, time.time() - start)

        parts = []
        for fc in fcs:
            override = on_tool(fc.name, fc.args) if on_tool else None
            out, err = (override, False) if isinstance(override, str) else _run_tool(functions, fc.name, fc.args)
            calls.append((fc.name, fc.args, err))
            if verbose:
                print(f"   🔧 {fc.name}({json.dumps(fc.args, default=str)[:90]}) → {out[:80]!r}{' ❌' if err else ''}")
            parts.append(function_response(fc, out, err))
        contents.append(types.Content(role="user", parts=parts))  # ALL results in ONE turn

        if tracker.total() - cost_at_start > max_cost:
            return AgentResult("[stopped: cost budget]", "budget", step, calls, time.time() - start)
        if time.time() - start > max_seconds:
            return AgentResult("[stopped: time budget]", "budget", step, calls, time.time() - start)

    return AgentResult("[stopped: step limit]", "step_limit", max_steps, calls, time.time() - start)
