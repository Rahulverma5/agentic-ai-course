import asyncio
import json
import sys
from pathlib import Path

from conftest import FakeClient, msg, text, tool

ROOT = Path(__file__).resolve().parent.parent


def test_mcp_server_tools(data_dir, monkeypatch):
    from mcp import Client

    from shopease.mcp_server import mcp

    monkeypatch.setenv("SHOPEASE_CUSTOMER_ID", "C001")

    async def run():
        async with Client(mcp) as c:  # in-memory transport, same API as stdio
            names = {t.name for t in (await c.list_tools()).tools}
            res = await c.call_tool("check_refund_eligibility", {"order_id": "O2002"})
            other = await c.call_tool("get_order", {"order_id": "O2003"})  # belongs to C002
            return names, res.content[0].text, other.content[0].text

    names, elig, other = asyncio.run(run())
    assert {"get_order", "check_refund_eligibility", "search_orders"} <= names
    assert json.loads(elig)["eligible"] is False
    assert other.startswith("Error")


def test_streaming_api(data_dir, monkeypatch):
    from fastapi.testclient import TestClient

    sys.path.insert(0, str(ROOT))
    import app as app_module
    from shopease.agent import SupportAgent

    fake = FakeClient([msg(tool("get_order", {"order_id": "O2001"}), stop="tool_use"),
                       msg(text("Your smart watch was delivered on 2026-11-08."))])
    monkeypatch.setattr(app_module, "SupportAgent",
                        lambda cid, **kw: SupportAgent(cid, client=fake, **(kw | {"stream": False})))
    r = TestClient(app_module.app).post("/chat", json={"conversation_id": "t1", "customer_id": "C001",
                                                       "message": "where is my watch?"})
    events = [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: ")]
    assert [e["type"] for e in events][0] == "route" and events[-1]["type"] == "done"
    assert any(e["type"] == "tool" for e in events) and events[-1]["tool_calls"] == ["get_order"]


def test_eval_runner_end_to_end(data_dir, monkeypatch):
    sys.path.insert(0, str(ROOT / "evals"))
    import run_evals

    class AlwaysText(FakeClient):
        def __init__(self):
            super().__init__([], route="faq")
            self.messages.create = lambda **kw: msg(text("Standard shipping takes 3-5 business days."))

    code = run_evals.main(["--only", "faq-shipping"], client=AlwaysText())
    assert code == 0
    assert "faq-shipping" in (ROOT / "evals" / "report.md").read_text()
