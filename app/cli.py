from __future__ import annotations

import sys

from agents import InsuranceAgentSystem


def safe_print(value: object = "") -> None:
    text = str(value)
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def main() -> None:
    agent_system = InsuranceAgentSystem()
    result = agent_system.ask(
        "Find a silver plan in Dallas Texas and explain what deductible means.",
        {"state": "TX", "county": "Dallas", "metal_level": "Silver"},
    )
    safe_print("\nAGENT TRACE\n")
    for step in result.trace:
        safe_print(f"{step.agent}: {step.action} -> {step.observation}")
    safe_print("\nANSWER\n")
    safe_print(result.answer)
    safe_print("\nMATCHING PLANS\n")
    safe_print(result.plans.to_string(index=False))
    safe_print("\nRETRIEVED DOCS\n")
    safe_print(result.retrieved_docs[["source", "title", "similarity"]].to_string(index=False))


if __name__ == "__main__":
    main()
