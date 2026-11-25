"""Test fixtures: fresh data per test + a scripted fake Gemini client (no API key, no network)."""
from __future__ import annotations

import pytest
from google.genai import types

from shopease import config
from shopease.data import setup_data


@pytest.fixture()
def data_dir(tmp_path):
    original = config.DATA_DIR
    config.set_data_dir(tmp_path)
    setup_data(force=True, quiet=True)
    yield tmp_path
    config.set_data_dir(original)


def msg(*parts, stop: str = "STOP") -> types.GenerateContentResponse:
    """A model response made of real SDK parts (text and/or function calls)."""
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=list(parts)),
                                    finish_reason=types.FinishReason.STOP)],
        usage_metadata=types.GenerateContentResponseUsageMetadata(prompt_token_count=1000, candidates_token_count=50))


def text(t: str) -> types.Part:
    return types.Part.from_text(text=t)


def tool(name: str, args: dict, id: str = "call_1") -> types.Part:
    return types.Part(function_call=types.FunctionCall(id=id, name=name, args=args))


class FakeModels:
    def __init__(self, script, route: str, default_text: str | None = None):
        self.script, self.route, self.default_text, self.calls = list(script), route, default_text, []

    def generate_content(self, *, model, contents, config=None):
        if config is not None and config.response_schema is not None:  # structured output: router / judge
            schema = config.response_schema
            parsed = schema(route=self.route, reason="fake") if "route" in schema.model_fields else \
                schema(passed=True, reason="fake")
            r = msg(text(parsed.model_dump_json()))
            r.parsed = parsed
            return r
        snapshot = list(contents) if isinstance(contents, list) else contents  # history keeps growing
        self.calls.append({"model": model, "contents": snapshot, "config": config})
        if not self.script and self.default_text is not None:
            return msg(text(self.default_text))
        return self.script.pop(0)

    def generate_content_stream(self, **kwargs):
        yield self.generate_content(**kwargs)


class FakeClient:
    """`FakeClient([msg(tool(...)), msg(text("done"))], route="order_issue")`"""

    def __init__(self, script, route: str = "order_issue", default_text: str | None = None):
        self.models = FakeModels(script, route, default_text)
