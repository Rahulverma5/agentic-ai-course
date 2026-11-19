"""Code graders: deterministic checks on the reply, the tool trajectory and the final DB/memory state."""
from __future__ import annotations

import sqlite3

from shopease import config, memory


def _alts(spec: str) -> list[str]:
    return spec.split("|")


def refund_status(order_id: str) -> str | None:
    con = sqlite3.connect(config.DB_PATH)
    row = con.execute("SELECT status FROM refunds WHERE order_id=? ORDER BY id DESC LIMIT 1", (order_id,)).fetchone()
    con.close()
    return row[0] if row else None


def refund_count() -> int:
    con = sqlite3.connect(config.DB_PATH)
    n = con.execute("SELECT COUNT(*) FROM refunds").fetchone()[0]
    con.close()
    return n


def grade(case: dict, reply) -> dict[str, bool]:
    """Returns {check_name: passed}. Only checks the case asks for are included."""
    text = (reply.text or "").lower()
    checks: dict[str, bool] = {}
    if "expect_route" in case:
        checks["route"] = reply.route == case["expect_route"]
    for spec in case.get("must_call", []):
        checks[f"called:{spec}"] = any(name in reply.tool_calls for name in _alts(spec))
    for name in case.get("must_not_call", []):
        checks[f"not_called:{name}"] = name not in reply.tool_calls
    if "reply_contains_any" in case:
        checks["reply_contains_any"] = any(s.lower() in text for s in case["reply_contains_any"])
    for s in case.get("reply_not_contains", []):
        checks[f"not_in_reply:{s}"] = s.lower() not in text
    for order_id, expected in case.get("refunds", {}).items():
        allowed = [None if a in (None, "null") else a for a in (_alts(expected) if expected else [None])]
        checks[f"refund:{order_id}"] = refund_status(order_id) in allowed
    if case.get("no_refunds"):
        checks["no_refunds"] = refund_count() == 0
    if "memory_no_fact_contains" in case:
        word = case["memory_no_fact_contains"].lower()
        checks["memory_policy"] = not any(f["kind"] == "fact" and word in f["text"].lower()
                                          for f in memory.load(case["customer_id"]))
    return checks
