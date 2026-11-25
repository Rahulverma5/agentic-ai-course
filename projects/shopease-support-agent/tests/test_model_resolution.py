from types import SimpleNamespace

import course_utils
from course_utils import llm
from shopease import config


def fake_list(names):
    return lambda: [SimpleNamespace(name=f"models/{n}", supported_actions=["generateContent"]) for n in names]


def test_pick_prefers_latest_then_stable_then_newest():
    names = ["gemini-3.5-flash", "gemini-3.8-flash-preview", "gemini-3.6-flash", "gemini-3.5-flash-lite",
             "gemini-3.8-flash-tts", "gemini-embedding-001", "gemini-3.1-pro-preview"]
    assert llm._pick(names, lite=False) == "gemini-3.6-flash"          # stable beats preview; tts skipped
    assert llm._pick(names, lite=True) == "gemini-3.5-flash-lite"
    assert llm._pick(names + ["gemini-flash-latest"], lite=False) == "gemini-flash-latest"


def test_resolve_switches_missing_models_everywhere(monkeypatch):
    monkeypatch.setattr(llm, "MODEL", "gemini-flash-latest")
    monkeypatch.setattr(llm, "CHEAP_MODEL", "gemini-flash-lite-latest")
    client = SimpleNamespace(models=SimpleNamespace(list=fake_list(["gemini-3.6-flash", "gemini-3.5-flash-lite"])))
    monkeypatch.setattr(llm, "get_client", lambda: client)
    model, cheap = llm.resolve_models(verbose=False)
    assert (model, cheap) == ("gemini-3.6-flash", "gemini-3.5-flash-lite")
    assert course_utils.MODEL == model and config.CHEAP_MODEL == cheap   # package + capstone updated


def test_resolve_keeps_available_models_and_survives_errors(monkeypatch):
    monkeypatch.setattr(llm, "MODEL", "gemini-3.6-flash")
    client = SimpleNamespace(models=SimpleNamespace(list=fake_list(["gemini-3.6-flash", "x-flash-lite"])))
    monkeypatch.setattr(llm, "get_client", lambda: client)
    assert llm.resolve_models(verbose=False)[0] == "gemini-3.6-flash"

    def boom():
        raise ConnectionError("offline")
    monkeypatch.setattr(llm, "get_client", lambda: SimpleNamespace(models=SimpleNamespace(list=boom)))
    assert llm.resolve_models(verbose=False)[0] == "gemini-3.6-flash"     # keeps config on failure
