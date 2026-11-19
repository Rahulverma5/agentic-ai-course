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
    try:
        r = client.messages.parse(model=config.CHEAP_MODEL, max_tokens=300, system=ROUTER_SYSTEM,
                                  output_format=Route,
                                  messages=[{"role": "user", "content": message}])
        if tracker:
            tracker.add(config.CHEAP_MODEL, r.usage, label="router")
        return r.parsed_output
    except Exception as e:  # never let the router take the whole system down
        print(f"[router] falling back to keywords ({type(e).__name__})")
        return heuristic_route(message)


FAQ_SYSTEM = """You answer general ShopEase policy questions using ONLY the policy passages provided.
Be brief (max 80 words), friendly, and cite sources like (returns.md#Return window).
If the passages don't answer the question, say you'll connect them with the support agent."""


def answer_faq(message: str, client, tracker=None) -> str:
    hits = rag.search(message, k=3)
    passages = "\n\n".join(f"<passage source=\"{h['source']}\">\n{h['text']}\n</passage>" for h in hits)
    r = client.messages.create(model=config.CHEAP_MODEL, max_tokens=600, system=FAQ_SYSTEM,
                               output_config={"effort": "low"},
                               messages=[{"role": "user", "content": f"{passages}\n\nQuestion: {message}"}])
    if tracker:
        tracker.add(config.CHEAP_MODEL, r.usage, label="faq")
    return "".join(b.text for b in r.content if b.type == "text")
