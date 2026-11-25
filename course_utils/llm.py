"""Gemini client setup (google-genai SDK) and a one-line `ask()` helper."""
from __future__ import annotations

import os
import re
import sys
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Optional: a .env file at the repo root (never commit it; it's in .gitignore).
try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except ImportError:  # python-dotenv is optional
    pass

# Google-maintained aliases always point at the current Flash / Flash-Lite releases, so the course
# keeps working as models are updated. Pin an exact model id with COURSE_MODEL / COURSE_CHEAP_MODEL.
MODEL = os.getenv("COURSE_MODEL", "gemini-flash-latest")                 # agents, harder reasoning
CHEAP_MODEL = os.getenv("COURSE_CHEAP_MODEL", "gemini-flash-lite-latest")  # bulk work: judges, routers

# Free-tier quotas are small (requests/minute and /day). The SDK retries 429/5xx with exponential backoff.
RETRY_STATUS_CODES = [408, 429, 500, 502, 503, 504]


def _api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


_SKIP = ("tts", "image", "embed", "live", "audio", "native", "robotics", "computer", "aqa", "learnlm", "gemma")


def _pick(names: list[str], lite: bool) -> str | None:
    """Best Flash (or Flash-Lite) model in a list: prefer -latest aliases, then stable, then the newest version."""
    cands = [n for n in names if "flash" in n and ("lite" in n) == lite and not any(s in n for s in _SKIP)]

    def rank(n):
        m = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
        return ("latest" in n, not any(t in n for t in ("preview", "exp")), float(m.group(1)) if m else 0.0)

    return max(cands, key=rank) if cands else None


def available_models() -> list[str]:
    """Model ids your key can call with generateContent (one API call)."""
    out = []
    for m in get_client().models.list():
        actions = m.supported_actions or []
        if not actions or "generateContent" in actions:
            out.append((m.name or "").removeprefix("models/"))
    return out


def resolve_models(verbose: bool = True) -> tuple[str, str]:
    """Make sure MODEL / CHEAP_MODEL exist for this key; if not, switch to the best available ones.

    Model names change over time (and differ by account and API version), so the course checks instead
    of trusting a hard-coded default. Pin your own choice with COURSE_MODEL / COURSE_CHEAP_MODEL.
    """
    global MODEL, CHEAP_MODEL
    try:
        names = available_models()
    except Exception as e:  # offline, bad key, ...: keep the configured names
        if verbose:
            print(f"(could not list models: {type(e).__name__}: {str(e)[:120]})")
        return MODEL, CHEAP_MODEL
    if not names:
        return MODEL, CHEAP_MODEL
    for var, lite in (("MODEL", False), ("CHEAP_MODEL", True)):
        current = globals()[var]
        if current in names:
            continue
        choice = _pick(names, lite) or _pick(names, not lite)
        if choice:
            if verbose:
                print(f"⚠️ {current} isn't available for this key; using {choice} for {var}. "
                      f"(Set COURSE_{var} to choose another.)")
            globals()[var] = choice
            os.environ[f"COURSE_{var}"] = choice
    for mod in ("course_utils", "shopease.config"):  # keep already-imported modules in sync
        if sys.modules.get(mod) is not None:
            sys.modules[mod].MODEL, sys.modules[mod].CHEAP_MODEL = MODEL, CHEAP_MODEL
    return MODEL, CHEAP_MODEL


def check_setup(resolve: bool = True) -> dict:
    """Check the Gemini key and pick working models. Run this first in every notebook."""
    ok = bool(_api_key())
    print(f"{'✅' if ok else '⬜'} GEMINI_API_KEY")
    if not ok:
        print("\nNo GEMINI_API_KEY found. Get a free key at https://aistudio.google.com/apikey, add it as a\n"
              "Codespaces secret (see SETUP.md) or put GEMINI_API_KEY=... in a .env file at the repo root,\n"
              "then restart the kernel.")
    elif resolve:
        resolve_models()
    print(f"\nMODEL={MODEL}  CHEAP_MODEL={CHEAP_MODEL}")
    return {"GEMINI_API_KEY": ok, "MODEL": MODEL, "CHEAP_MODEL": CHEAP_MODEL}


@lru_cache(maxsize=1)
def get_client():
    from google import genai
    from google.genai import types

    key = _api_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set. See SETUP.md (Codespaces secret or .env file).")
    http = types.HttpOptions(
        base_url=os.getenv("GEMINI_BASE_URL") or None,  # optional: a proxy or a local test stub
        api_version=os.getenv("GEMINI_API_VERSION", "v1beta"),  # Gemini developer features + -latest aliases
        retry_options=types.HttpRetryOptions(attempts=6, initial_delay=2.0, max_delay=60.0, exp_base=2.0,
                                             jitter=1.0, http_status_codes=RETRY_STATUS_CODES),
    )
    return genai.Client(api_key=key, http_options=http)


def text_of(response) -> str:
    """Join the visible text parts of a response (skips thought summaries; safe with function calls)."""
    if not response or not response.candidates:
        return ""
    content = response.candidates[0].content
    if not content or not content.parts:
        return ""
    return "".join(p.text for p in content.parts if p.text and not p.thought)


def thinking(level: str | None):
    """ThinkingConfig from a level name: 'minimal' | 'low' | 'medium' | 'high' (None = model default)."""
    if not level:
        return None
    from google.genai import types

    return types.ThinkingConfig(thinking_level=level.upper())


def user(text: str):
    """A user turn as a Content object (handy for building conversation lists)."""
    from google.genai import types

    return types.Content(role="user", parts=[types.Part.from_text(text=text)])


def ask(prompt: str, model: str | None = None, system: str | None = None, max_tokens: int | None = None,
        thinking_level: str | None = None, track: bool = True, **config) -> str:
    """One prompt in, text out. Defaults to the CHEAP model to stay inside free-tier quotas."""
    from google.genai import types

    from .cost import tracker

    model = model or CHEAP_MODEL  # looked up at call time (check_setup may have switched it)
    cfg = types.GenerateContentConfig(system_instruction=system, max_output_tokens=max_tokens,
                                      thinking_config=thinking(thinking_level), **config)
    response = get_client().models.generate_content(model=model, contents=prompt, config=cfg)
    if track:
        tracker.add(model, response.usage_metadata, label="ask")
    return text_of(response)
