import sys
from pathlib import Path

from conftest import FakeClient, msg, text, tool

from shopease import guardrails, rag, router
from shopease.agent import HANDOFF_TEXT, SupportAgent

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evals"))
from graders import grade  # noqa: E402


def test_agent_loop_runs_tools_and_answers(data_dir):
    client = FakeClient([
        msg(tool("check_refund_eligibility", {"order_id": "O2002"})),
        msg(text("Sorry, O2002 was delivered 36 days ago, outside our 30-day window.")),
    ])
    agent = SupportAgent("C001", client=client)
    reply = agent.chat("Refund my coffee grinder O2002")
    assert reply.route == "order_issue" and reply.tool_calls == ["check_refund_eligibility"]
    assert "30-day" in reply.text and reply.steps == 2
    # the function result was sent back, matched by id and name
    last_user = client.models.calls[1]["contents"][-1]
    fr = last_user.parts[0].function_response
    assert last_user.role == "user" and fr.id == "call_1" and fr.name == "check_refund_eligibility"
    assert '"eligible": false' in fr.response["output"]
    # the system instruction is identical on every call: a stable prefix for Gemini's implicit cache
    cfg0, cfg1 = client.models.calls[0]["config"], client.models.calls[1]["config"]
    assert cfg0.system_instruction == cfg1.system_instruction and "ShopEase" in cfg0.system_instruction


def test_repeat_detection_and_step_limit(data_dir):
    loop = [msg(tool("get_order", {"order_id": "O2001"}, id=f"t{i}")) for i in range(4)]
    agent = SupportAgent("C001", client=FakeClient(loop), max_steps=4)
    reply = agent.chat("where is my order")
    assert reply.stop_reason == "step_limit"
    third = agent.history[6].parts[0].function_response  # user msg, (model, results) x3 → index 6 = 3rd results
    assert "already called" in third.response["error"]


def test_output_guard_blocks_leaks(data_dir):
    client = FakeClient([msg(text("Sure! That order belongs to ben@example.com."))])
    reply = SupportAgent("C001", client=client).chat("whose order is O2003?")
    assert reply.text == guardrails.SAFE_FALLBACK and reply.guard_problems


def test_human_route_skips_agent(data_dir):
    client = FakeClient([], route="human")
    reply = SupportAgent("C002", client=client).chat("I want a manager")
    assert reply.text == HANDOFF_TEXT and client.models.calls == []


def test_router_fallback_and_pii_masking():
    class Broken:
        class models:
            @staticmethod
            def generate_content(**kw):
                raise ConnectionError("offline")
    assert router.classify("I will sue you", Broken).route == "human"
    assert router.classify("where is my order O2001", Broken).route == "order_issue"
    assert "4111" not in guardrails.mask_pii("card 4111 1111 1111 1111")


def test_bm25_finds_policy(data_dir):
    rag.reset_index()
    hits = rag.search("how many days do I have to return an item", k=3, mode="bm25")
    assert any(h["source"].startswith("returns.md") for h in hits)
    hits = rag.search("smart watch warranty years", k=2, mode="bm25")
    assert hits[0]["source"].startswith("warranty.md")


def test_graders(data_dir):
    client = FakeClient([msg(text("Your refund request is waiting for a specialist."))])
    reply = SupportAgent("C001", client=client).chat("refund O2001")
    case = {"customer_id": "C001", "expect_route": "order_issue", "must_call": ["check_refund_eligibility"],
            "reply_not_contains": ["has been refunded"], "refunds": {"O2001": "pending_approval|null"}}
    checks = grade(case, reply)
    assert checks["route"] and checks["not_in_reply:has been refunded"] and checks["refund:O2001"]
    assert checks["called:check_refund_eligibility"] is False  # the fake skipped the required tool → caught
