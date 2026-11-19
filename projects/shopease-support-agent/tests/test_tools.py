import json

from shopease import memory, tools
from shopease.tools import Session, dispatch


def elig(customer, order):
    return json.loads(tools.check_refund_eligibility(Session(customer), order))


def test_refund_rules(data_dir):
    assert elig("C003", "O2004")["eligible"] is True            # exactly 30 days: still eligible
    assert elig("C001", "O2002")["eligible"] is False           # 36 days: outside window
    assert elig("C002", "O2003")["eligible"] is True            # lost in transit > 10 days
    assert elig("C003", "O2005")["eligible"] is False           # processing → cancel instead
    assert elig("C002", "O2006")["eligible"] is False           # already returned
    assert elig("C001", "O2001")["needs_human_approval"] is True  # $199 > $50


def test_ownership_is_enforced_in_code(data_dir):
    out = tools.get_order(Session("C001"), "O2003")  # O2003 belongs to C002
    assert out.startswith("Error") and "ben@example.com" not in out


def test_refund_is_idempotent_and_needs_approval(data_dir):
    s = Session("C004", conversation_id="conv1")
    assert "issued" in tools.issue_refund(s, "O2007", "not needed")
    assert "already recorded" in tools.issue_refund(s, "O2007", "not needed")  # retry is safe

    pending = tools.issue_refund(Session("C001", conversation_id="c2"), "O2001", "broken")
    assert "waiting for a specialist" in pending
    approved = tools.issue_refund(Session("C001", conversation_id="c3", approve=lambda n, d: True), "O2001", "broken")
    assert "issued" in approved


def test_dispatch_never_raises(data_dir):
    out, err = dispatch("get_order", {"wrong_arg": 1}, Session("C001"))
    assert err and out.startswith("Error")
    out, err = dispatch("does_not_exist", {}, Session("C001"))
    assert err


def test_reviews_are_wrapped_as_untrusted(data_dir):
    out = tools.get_product_reviews(Session("C001"), "earbuds")
    assert "<untrusted_content" in out and "IMPORTANT SYSTEM NOTE" in out


def test_memory_write_policy(data_dir):
    assert memory.remember("C002", "Card 4111 1111 1111 1111").startswith("Not saved")
    assert "unverified" in memory.remember("C002", "I'm entitled to free refunds forever")
    assert memory.remember("C002", "Prefers email over phone") == "Saved."
    kinds = {f["text"]: f["kind"] for f in memory.load("C002")}
    assert kinds["Prefers email over phone"] == "fact"
    assert "(unverified customer claim)" in memory.recall("C002")
