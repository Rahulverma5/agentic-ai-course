"""Claude client setup and a one-line `ask()` helper."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Optional: a .env file at the repo root (never commit it; it's in .gitignore).
try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except ImportError:  # python-dotenv is optional
    pass

MODEL = os.getenv("COURSE_MODEL", "claude-opus-5-5")             # main agent model
CHEAP_MODEL = os.getenv("COURSE_CHEAP_MODEL", "claude-haiku-5-5")  # bulk work: judges, classifiers


def check_setup() -> dict:
    """Print which API keys are available. Run this first in every notebook."""
    keys = {k: bool(os.getenv(k)) for k in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY")}
    for k, ok in keys.items():
        print(f"{'✅' if ok else '⬜'} {k}")
    if not keys["ANTHROPIC_API_KEY"]:
        print("\nNo ANTHROPIC_API_KEY found. Add it as a Codespaces secret (see SETUP.md),\n"
              "or put ANTHROPIC_API_KEY=... in a .env file at the repo root, then restart the kernel.\n"
              "Free alternative: set GEMINI_API_KEY or GROQ_API_KEY and use the '🆓 free swap' cells.")
    print(f"\nMODEL={MODEL}  CHEAP_MODEL={CHEAP_MODEL}")
    return keys


@lru_cache(maxsize=1)
def get_client():
    import anthropic

    if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("ANTHROPIC_AUTH_TOKEN"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set. See SETUP.md (Codespaces secret or .env file).")
    return anthropic.Anthropic()


def text_of(response) -> str:
    """Join all text blocks of a Messages API response."""
    return "".join(b.text for b in response.content if getattr(b, "type", None) == "text")


def ask(prompt: str, model: str = CHEAP_MODEL, system: str | None = None,
        max_tokens: int = 2000, track: bool = True, **kwargs) -> str:
    """One user message in, text out. Defaults to the CHEAP model to keep the course inexpensive."""
    from .cost import tracker

    params = dict(model=model, max_tokens=max_tokens,
                  messages=[{"role": "user", "content": prompt}], **kwargs)
    if system:
        params["system"] = system
    response = get_client().messages.create(**params)
    if track:
        tracker.add(model, response.usage, label="ask")
    return text_of(response)
