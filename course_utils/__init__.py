"""Small helpers shared by the course notebooks (Gemini, google-genai SDK).

Early notebooks build everything from scratch on purpose. From Week 2 on, notebooks import
these helpers so the cells can focus on the new idea of the day.

    from course_utils import client, MODEL, CHEAP_MODEL, ask, tracker, run_agent
"""
from .llm import MODEL, CHEAP_MODEL, REPO_ROOT, check_setup, get_client, ask, text_of, thinking, user
from .cost import CostTracker, tracker, PRICES
from .loop import run_agent, AgentResult, to_gemini_tools, function_response


class _LazyClient:
    """`client` is created on first use, so importing course_utils never fails without a key."""

    def __getattr__(self, name):
        return getattr(get_client(), name)


client = _LazyClient()

__all__ = [
    "MODEL", "CHEAP_MODEL", "REPO_ROOT", "check_setup", "get_client", "client", "ask", "text_of", "thinking",
    "user", "CostTracker", "tracker", "PRICES", "run_agent", "AgentResult", "to_gemini_tools", "function_response",
]
