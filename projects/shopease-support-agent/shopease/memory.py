"""Per-customer long-term memory: a small JSON file of facts, with a write policy enforced in code."""
from __future__ import annotations

import json
import re
from datetime import datetime

from . import config
from .guardrails import contains_sensitive

MAX_FACTS = 20
ENTITLEMENT_WORDS = re.compile(r"\b(entitled|free refunds?|always refund|lifetime|admin|vip access)\b", re.I)


def _path(customer_id: str):
    config.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    return config.MEMORY_DIR / f"{customer_id}.json"


def load(customer_id: str) -> list[dict]:
    p = _path(customer_id)
    return json.loads(p.read_text()) if p.exists() else []


def remember(customer_id: str, fact: str) -> str:
    fact = fact.strip()
    if contains_sensitive(fact):
        return "Not saved: memory must never contain payment details or passwords."
    if not fact or len(fact) > 300:
        return "Not saved: a fact must be one short sentence."
    kind = "claim" if ENTITLEMENT_WORDS.search(fact) else "fact"  # memory-poisoning defense
    facts = [f for f in load(customer_id) if f["text"].lower() != fact.lower()]
    facts.append({"text": fact, "kind": kind, "updated_at": datetime.now().isoformat(timespec="seconds")})
    _path(customer_id).write_text(json.dumps(facts[-MAX_FACTS:], indent=2))
    return "Saved." if kind == "fact" else "Saved as an unverified customer claim (not a policy exception)."


def recall(customer_id: str) -> str:
    facts = load(customer_id)
    if not facts:
        return "(no saved notes for this customer)"
    lines = [f"- {f['text']}" if f["kind"] == "fact" else f"- (unverified customer claim) {f['text']}" for f in facts]
    return "\n".join(lines)


def forget(customer_id: str) -> None:
    """Right to be forgotten."""
    _path(customer_id).unlink(missing_ok=True)
