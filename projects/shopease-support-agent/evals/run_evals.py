"""Run the ShopEase eval suite (Day 11). Each case runs on a fresh copy of the data.

    python evals/run_evals.py                     # all cases once
    python evals/run_evals.py --repeats 3         # reliability: reports pass^3
    python evals/run_evals.py --only refund       # cases whose id contains 'refund'
    python evals/run_evals.py --judge             # add a cheap LLM judge for tone/honesty

Writes evals/report.md and evals/results.jsonl. Exits with code 1 if any CRITICAL case fails or the
pass rate is below --min-pass, so it can gate a CI pipeline.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from pydantic import BaseModel  # noqa: E402

from graders import grade  # noqa: E402
from shopease import config  # noqa: E402
from shopease.agent import SupportAgent  # noqa: E402
from shopease.data import setup_data  # noqa: E402


class Verdict(BaseModel):
    passed: bool
    reason: str


JUDGE_RUBRIC = ("Pass only if the reply is polite, concise, does not invent facts or promises, "
                "and gives the customer a clear next step.")


def judge(client, question: str, reply: str) -> Verdict:
    r = client.messages.parse(model=config.CHEAP_MODEL, max_tokens=500, output_format=Verdict,
                              messages=[{"role": "user", "content": f"Rubric: {JUDGE_RUBRIC}\n\nCustomer: {question}"
                                                                    f"\n\nAgent reply: {reply}\n\nDoes the reply pass?"}])
    return r.parsed_output


def run_case(case: dict, client=None, use_judge: bool = False) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        config.set_data_dir(tmp)
        setup_data(force=True, quiet=True)
        agent = SupportAgent(case["customer_id"], client=client, conversation_id=f"eval-{case['id']}")
        t0 = time.time()
        try:
            reply = agent.chat(case["input"])
            checks = grade(case, reply)
            error = None
        except Exception as e:
            reply, checks, error = None, {"no_exception": False}, f"{type(e).__name__}: {e}"
        seconds = time.time() - t0
        if use_judge and reply:
            v = judge(agent.client, case["input"], reply.text)
            checks["judge"] = v.passed
    return {"id": case["id"], "critical": case.get("critical", False), "passed": all(checks.values()),
            "checks": checks, "reply": reply.text if reply else None, "route": reply.route if reply else None,
            "tool_calls": reply.tool_calls if reply else [], "cost": reply.cost if reply else 0.0,
            "seconds": round(seconds, 2), "error": error}


def write_report(results: list[dict], repeats: int, path: Path) -> dict:
    by_case: dict[str, list[dict]] = {}
    for r in results:
        by_case.setdefault(r["id"], []).append(r)
    pass_rate = sum(r["passed"] for r in results) / len(results)
    pass_all = sum(all(x["passed"] for x in rs) for rs in by_case.values()) / len(by_case)  # pass^k
    secs = sorted(r["seconds"] for r in results)
    p95 = secs[min(len(secs) - 1, int(0.95 * len(secs)))]
    critical_fail = sorted({r["id"] for r in results if r["critical"] and not r["passed"]})
    summary = {"cases": len(by_case), "runs": len(results), "pass_rate": pass_rate, f"pass^{repeats}": pass_all,
               "cost_total": sum(r["cost"] for r in results), "p50_s": statistics.median(secs), "p95_s": p95,
               "critical_failures": critical_fail}
    lines = ["# ShopEase eval report", "",
             f"- Cases: **{len(by_case)}** × {repeats} run(s)",
             f"- Pass rate (all runs): **{pass_rate:.0%}**",
             f"- pass^{repeats} (case passes every run): **{pass_all:.0%}**",
             f"- Cost: **${summary['cost_total']:.4f}** · Latency p50 {summary['p50_s']:.1f}s · p95 {p95:.1f}s",
             f"- Critical failures: **{', '.join(critical_fail) or 'none'}**", "",
             "| Case | Critical | Passed runs | Failed checks |", "|---|---|---|---|"]
    for cid, rs in by_case.items():
        failed = sorted({k for r in rs for k, ok in r["checks"].items() if not ok})
        lines.append(f"| {cid} | {'⚠️' if rs[0]['critical'] else ''} | {sum(r['passed'] for r in rs)}/{len(rs)} | "
                     f"{', '.join(failed) or '—'} |")
    path.write_text("\n".join(lines) + "\n")
    return summary


def main(argv=None, client=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--only", default="")
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--min-pass", type=float, default=0.8)
    args = ap.parse_args(argv)

    cases = [json.loads(line) for line in (HERE / "cases.jsonl").read_text().splitlines() if line.strip()]
    cases = [c for c in cases if args.only in c["id"]]
    original_dir = config.DATA_DIR
    results = []
    try:
        for case in cases:
            for i in range(args.repeats):
                r = run_case(case, client=client, use_judge=args.judge)
                results.append(r)
                print(f"{'✅' if r['passed'] else '❌'} {case['id']:<28} run {i + 1}  "
                      f"{[k for k, ok in r['checks'].items() if not ok] or ''}")
    finally:
        config.set_data_dir(original_dir)

    (HERE / "results.jsonl").write_text("\n".join(json.dumps(r, default=str) for r in results) + "\n")
    summary = write_report(results, args.repeats, HERE / "report.md")
    print(json.dumps(summary, indent=2))
    failed = bool(summary["critical_failures"]) or summary["pass_rate"] < args.min_pass
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
