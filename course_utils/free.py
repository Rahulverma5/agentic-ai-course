"""Free alternative: run the same ideas on Gemini or Groq via their OpenAI-compatible endpoints.

Model names and free-tier limits change often. Override them with environment variables
FREE_GEMINI_MODEL / FREE_GROQ_MODEL if a default stops working.
"""
from __future__ import annotations

import json
import os
from typing import Callable

FREE_PROVIDERS = {
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
               "key": "GEMINI_API_KEY", "model": os.getenv("FREE_GEMINI_MODEL", "gemini-2.5-flash")},
    "groq": {"base_url": "https://api.groq.com/openai/v1",
             "key": "GROQ_API_KEY", "model": os.getenv("FREE_GROQ_MODEL", "llama-3.3-70b-versatile")},
}


def to_openai_tools(tools: list[dict]) -> list[dict]:
    """Claude tool format → OpenAI 'function' tool format."""
    return [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""),
                                              "parameters": t["input_schema"]}} for t in tools]


def _client(provider: str):
    from openai import OpenAI

    cfg = FREE_PROVIDERS[provider]
    if not os.getenv(cfg["key"]):
        raise RuntimeError(f"{cfg['key']} is not set (see SETUP.md).")
    return OpenAI(base_url=cfg["base_url"], api_key=os.environ[cfg["key"]]), cfg["model"]


def free_chat(provider: str, prompt: str, system: str | None = None, client=None) -> str:
    oa, model = (client, FREE_PROVIDERS[provider]["model"]) if client else _client(provider)
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    r = oa.chat.completions.create(model=model, messages=msgs)
    return r.choices[0].message.content or ""


def free_run_agent(provider: str, prompt: str, tools: list[dict], functions: dict[str, Callable],
                   system: str | None = None, max_steps: int = 10, verbose: bool = True, client=None) -> str:
    """The same think → act → observe loop, in the OpenAI wire format.

    Differences from Claude's format: tool calls arrive in `message.tool_calls`, arguments are a JSON
    *string*, and each result goes back as its own {"role": "tool", "tool_call_id": ...} message.
    """
    oa, model = (client, FREE_PROVIDERS[provider]["model"]) if client else _client(provider)
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    for _ in range(max_steps):
        r = oa.chat.completions.create(model=model, messages=msgs, tools=to_openai_tools(tools))
        m = r.choices[0].message
        msgs.append(m.model_dump(exclude_none=True))
        if not m.tool_calls:
            return m.content or ""
        for tc in m.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
                out = functions[tc.function.name](**args)
                out = out if isinstance(out, str) else json.dumps(out, default=str)
            except Exception as e:
                out = f"Error: {type(e).__name__}: {e}"
            if verbose:
                print(f"   🔧 {tc.function.name}({tc.function.arguments[:80]}) → {out[:80]!r}")
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": out})
    return "[stopped: step limit]"
