"""ShopEase streaming chat API (Day 15).

    uvicorn app:app --reload --port 8000        # run from projects/shopease-support-agent/

    curl -N -X POST localhost:8000/chat -H 'content-type: application/json' \
         -d '{"conversation_id": "c1", "customer_id": "C001", "message": "Where is my smart watch?"}'

In Codespaces, port 8000 is forwarded automatically (see the PORTS tab).
Production notes: authenticate the customer (never trust customer_id from the body), and keep
conversations in Redis/a DB instead of process memory so the API can scale and survive restarts.
"""
from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from shopease.agent import SupportAgent

app = FastAPI(title="ShopEase Support Agent")
CONVERSATIONS: dict[str, SupportAgent] = {}  # demo only: in-process memory


class ChatIn(BaseModel):
    conversation_id: str
    customer_id: str  # DEMO ONLY: in production this comes from the auth token
    message: str


@app.get("/health")
def health():
    return {"ok": True, "conversations": len(CONVERSATIONS)}


@app.post("/chat")
def chat(body: ChatIn):
    agent = CONVERSATIONS.get(body.conversation_id)
    if agent is None or agent.session.customer_id != body.customer_id:
        agent = CONVERSATIONS[body.conversation_id] = SupportAgent(
            body.customer_id, conversation_id=body.conversation_id, stream=True)

    def events():
        for ev in agent.chat_events(body.message):
            if ev["type"] == "done":
                r = ev["reply"]
                ev = {"type": "done", "route": r.route, "steps": r.steps, "cost": round(r.cost, 5),
                      "tool_calls": r.tool_calls, "stop_reason": r.stop_reason}
            yield f"data: {json.dumps(ev, default=str)}\n\n"  # Server-Sent Events

    return StreamingResponse(events(), media_type="text/event-stream")
