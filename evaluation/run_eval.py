from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

os.environ["MISTRAL_API_KEY"] = ""

from agents import InsuranceAgentSystem  # noqa: E402


def assert_check(check: str, run) -> None:
    if check == "plans_non_empty":
        assert len(run.plans) > 0, "expected at least one structured plan"
    elif check == "trace_has_plan_search":
        assert any(step.agent == "plan_search_agent" for step in run.trace), "missing plan search agent trace"
    elif check == "trace_has_retrieval":
        assert any(step.agent == "retrieval_agent" for step in run.trace), "missing retrieval agent trace"
    elif check == "retrieved_deductible":
        titles = " ".join(str(v) for v in run.retrieved_docs.get("title", []))
        assert "Deductible" in titles, "deductible document was not retrieved"
    elif check == "security_blocks":
        assert not run.security.allowed, "security guard should block this request"
    elif check == "graph_non_empty":
        assert run.graph.get("nodes", 0) > 0 and run.graph.get("edges", 0) > 0, "graph summary is empty"
    else:
        raise AssertionError(f"unknown check: {check}")


def main() -> int:
    questions = json.loads((ROOT / "evaluation" / "questions.json").read_text(encoding="utf-8"))
    system = InsuranceAgentSystem()
    failures: list[str] = []
    for item in questions:
        run = system.ask(item["question"], item.get("filters") or {})
        for check in item["checks"]:
            try:
                assert_check(check, run)
            except AssertionError as exc:
                failures.append(f"{item['id']}::{check}: {exc}")
    if failures:
        print("FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"PASS {len(questions)} evaluation scenarios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
