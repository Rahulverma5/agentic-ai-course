"""Central settings. Paths are read at call time (config.DB_PATH) so tests/evals can redirect them."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("SHOPEASE_DATA_DIR", PROJECT_DIR / "data"))
DB_PATH = DATA_DIR / "shopease.db"
POLICY_DIR = DATA_DIR / "policies"
MEMORY_DIR = DATA_DIR / "memory"
TRACE_DIR = DATA_DIR / "traces"

MODEL = os.getenv("COURSE_MODEL", "claude-opus-5-5")
CHEAP_MODEL = os.getenv("COURSE_CHEAP_MODEL", "claude-haiku-5-5")

# Business rules live in code, not in the prompt.
RETURN_WINDOW_DAYS = 30
LOST_SHIPMENT_DAYS = 10
REFUND_APPROVAL_LIMIT = 50.0  # refunds above this need a human

# A fixed "today" keeps the synthetic data and the evals reproducible.
TODAY = date.fromisoformat(os.getenv("SHOPEASE_TODAY", "2026-11-20"))


def set_data_dir(path: str | Path) -> None:
    """Point every module at another data folder (used by evals and tests)."""
    global DATA_DIR, DB_PATH, POLICY_DIR, MEMORY_DIR, TRACE_DIR
    DATA_DIR = Path(path)
    DB_PATH = DATA_DIR / "shopease.db"
    POLICY_DIR = DATA_DIR / "policies"
    MEMORY_DIR = DATA_DIR / "memory"
    TRACE_DIR = DATA_DIR / "traces"
