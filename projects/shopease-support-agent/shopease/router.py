"""Triage router (workflow before agent): cheap model + structured output, with a keyword fallback."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

from . import config, rag


class Route(BaseModel):
    route: Literal["faq", "order_issue", "human"]
    reason: str


ROUTER_SYSTEM = """You triage ShopEase customer-support messages. Pick exactly one route:
- faq: a general policy/how-to question that needs no account data (return window, shipping times, warranty length).
- order_issue: anything about this customer's own orders, refunds, deliveries, account, or that needs account data.
- human: legal threats, abuse, safety issues, or the customer explicitly asks for a human/manager.
When unsure between faq and order_issue, choose order_issue."""

HUMAN_PAT = re.compile(r"\b(lawyer|legal action|sue|human|manager|real person|complaint to)\b", re.I)
ORDER_PAT = re.compile(r"\b(O\d{4}|my order|my refund|refund me|where is my|haven't received|didn't arrive|"
                       r"my account|cancel my|track)\b", re.I)


def heuristic_route(message: str) -> Route:
    if HUMAN_PAT.search(message):
        return Route(route="human", reason="keyword fallback")
    if ORDER_PAT.search(message):
        return Route(route="order_issue", reason="keyword fallback")
    return Route(route="faq", reason="keyword fallback")


def classify(message: str, client, tracker=None) -> Route:
    from google.genai import types

    try:
        r = client.models.generate_content(
            model=config.CHEAP_MODEL, contents=message,
            config=types.GenerateContentConfig(system_instruction=ROUTER_SYSTEM, response_mime_type="application/json",
                                               response_schema=Route))  # structured output → r.parsed
        if tracker:
            tracker.add(config.CHEAP_MODEL, r.usage_metadata, label="router")
        if r.parsed is None:
            raise ValueError("no structured output")
        return r.parsed
    except Exception as e:  # never let the router take the whole system down
        print(f"[router] falling back to keywords ({type(e).__name__})")
        return heuristic_route(message)


FAQ_SYSTEM = """You answer general ShopEase policy questions using ONLY the policy passages provided.
Be brief (max 80 words), friendly, and cite sources like (returns.md#Return window).
If the passages don't answer the question, say you'll connect them with the support agent."""


def answer_faq(message: str, client, tracker=None) -> str:
    from google.genai import types

    from course_utils.llm import text_of

    hits = rag.search(message, k=3)
    passages = "\n\n".join(f"<passage source=\"{h['source']}\">\n{h['text']}\n</passage>" for h in hits)
    r = client.models.generate_content(
        model=config.CHEAP_MODEL, contents=f"{passages}\n\nQuestion: {message}",
        config=types.GenerateContentConfig(system_instruction=FAQ_SYSTEM, max_output_tokens=600))
    if tracker:
        tracker.add(config.CHEAP_MODEL, r.usage_metadata, label="faq")
    return text_of(r)
