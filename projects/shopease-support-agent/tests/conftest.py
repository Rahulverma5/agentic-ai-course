"""Test fixtures: fresh data per test + a scripted fake Claude client (no API key, no network)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from anthropic.types import Message, TextBlock, ToolUseBlock, Usage

from shopease import config
from shopease.data import setup_data


@pytest.fixture()
def data_dir(tmp_path):
    original = config.DATA_DIR
    config.set_data_dir(tmp_path)
    setup_data(force=True, quiet=True)
    yield tmp_path
    config.set_data_dir(original)


def msg(*blocks, stop: str = "end_turn") -> Message:
    return Message(id="msg_test", type="message", role="assistant", model=config.MODEL, content=list(blocks),
                   stop_reason=stop, stop_sequence=None, usage=Usage(input_tokens=1000, output_tokens=50))


def text(t: str) -> TextBlock:
    return TextBlock(type="text", text=t)


def tool(name: str, args: dict, id: str = "toolu_1") -> ToolUseBlock:
    return ToolUseBlock(type="tool_use", id=id, name=name, input=args)


class FakeMessages:
    def __init__(self, script: list[Message], route: str):
        self.script, self.route, self.calls = list(script), route, []

    def create(self, **kwargs):
        self.calls.append(kwargs | {"messages": list(kwargs["messages"])})  # snapshot: history keeps growing
        return self.script.pop(0)

    def parse(self, **kwargs):
        from shopease.router import Route

        return SimpleNamespace(parsed_output=Route(route=self.route, reason="fake"),
                               usage=Usage(input_tokens=100, output_tokens=10))


class FakeClient:
    """`FakeClient([msg(tool(...), stop="tool_use"), msg(text("done"))], route="order_issue")`"""

    def __init__(self, script: list[Message], route: str = "order_issue"):
        self.messages = FakeMessages(script, route)
