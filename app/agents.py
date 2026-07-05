from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import pandas as pd

try:
    from .knowledge_graph import build_knowledge_graph, graph_summary
    from .rag_pipeline import InsuranceCopilot
    from .security import SecurityDecision, SecurityGuard
except ImportError:
    from knowledge_graph import build_knowledge_graph, graph_summary
    from rag_pipeline import InsuranceCopilot
    from security import SecurityDecision, SecurityGuard


@dataclass
class AgentStep:
    agent: str
    action: str
    observation: str


@dataclass
class AgentRun:
    question: str
    answer: str
    plans: pd.DataFrame
    retrieved_docs: pd.DataFrame
    keyword_docs: pd.DataFrame
    graph: dict[str, Any]
    security: SecurityDecision
    trace: list[AgentStep] = field(default_factory=list)


class Agent(Protocol):
    name: str

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        ...


class SecurityAgent:
    name = "security_agent"

    def __init__(self, guard: SecurityGuard) -> None:
        self.guard = guard

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        decision = self.guard.analyze(state["question"])
        state["security"] = decision
        state["trace"].append(
            AgentStep(
                self.name,
                "analyze_question",
                "allowed" if decision.allowed else decision.reason,
            )
        )
        return state


class PlannerAgent:
    name = "planner_agent"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        question = state["question"].lower()
        tasks = ["security_check", "structured_plan_search", "rag_retrieval", "answer_synthesis"]
        if any(term in question for term in ["graph", "relationship", "issuer", "metal"]):
            tasks.insert(-1, "knowledge_graph_summary")
        else:
            tasks.insert(-1, "knowledge_graph_summary")
        state["tasks"] = tasks
        state["trace"].append(AgentStep(self.name, "create_plan", " -> ".join(tasks)))
        return state


class PlanSearchAgent:
    name = "plan_search_agent"

    def __init__(self, copilot: InsuranceCopilot) -> None:
        self.copilot = copilot

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        filters = state.get("filters") or {}
        plans = self.copilot.search_plans(
            state=filters.get("state"),
            county=filters.get("county"),
            metal_level=filters.get("metal_level"),
            max_premium=filters.get("max_premium"),
        )
        state["plans"] = plans
        state["trace"].append(
            AgentStep(self.name, "search_plans", f"returned {len(plans):,} matching plans")
        )
        return state


class RetrievalAgent:
    name = "retrieval_agent"

    def __init__(self, copilot: InsuranceCopilot) -> None:
        self.copilot = copilot

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        question = state["question"]
        state["vector_results"] = self.copilot.vector_search(question)
        state["keyword_results"] = self.copilot.keyword_search(question)
        state["trace"].append(
            AgentStep(
                self.name,
                "hybrid_retrieve",
                f"vector={len(state['vector_results'])}, keyword={len(state['keyword_results'])}",
            )
        )
        return state


class KnowledgeGraphAgent:
    name = "knowledge_graph_agent"

    def __init__(self, copilot: InsuranceCopilot) -> None:
        self.copilot = copilot

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        graph = build_knowledge_graph(self.copilot.plans_df)
        summary = graph_summary(graph)
        state["graph"] = {
            "nodes": summary.nodes,
            "edges": summary.edges,
            "top_relations": summary.top_relations,
        }
        state["trace"].append(
            AgentStep(
                self.name,
                "summarize_graph",
                f"nodes={summary.nodes:,}, edges={summary.edges:,}",
            )
        )
        return state


class AnswerSynthesisAgent:
    name = "answer_synthesis_agent"

    def __init__(self, copilot: InsuranceCopilot, guard: SecurityGuard) -> None:
        self.copilot = copilot
        self.guard = guard

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        search_result = type(
            "SearchResultLike",
            (),
            {
                "plans": state["plans"],
                "vector_results": state["vector_results"],
                "keyword_results": state["keyword_results"],
            },
        )()
        prompt = self.copilot.build_prompt(state["question"], search_result)
        answer = self.copilot.call_mistral(prompt)
        state["answer"] = self.guard.attach_disclaimer(answer)
        state["trace"].append(
            AgentStep(self.name, "synthesize_answer", "generated answer from structured facts and retrieved sources")
        )
        return state


class InsuranceAgentSystem:
    """ADK-style explicit multi-agent orchestration around the RAG pipeline."""

    def __init__(self, copilot: InsuranceCopilot | None = None, guard: SecurityGuard | None = None) -> None:
        self.copilot = copilot or InsuranceCopilot()
        self.guard = guard or SecurityGuard()
        self.security_agent = SecurityAgent(self.guard)
        self.planner_agent = PlannerAgent()
        self.plan_search_agent = PlanSearchAgent(self.copilot)
        self.retrieval_agent = RetrievalAgent(self.copilot)
        self.graph_agent = KnowledgeGraphAgent(self.copilot)
        self.answer_agent = AnswerSynthesisAgent(self.copilot, self.guard)

    def ask(self, question: str, filters: dict[str, Any] | None = None) -> AgentRun:
        state: dict[str, Any] = {
            "question": question,
            "filters": filters or {},
            "trace": [],
        }
        state = self.security_agent.run(state)
        if not state["security"].allowed:
            return AgentRun(
                question=question,
                answer=self.guard.refusal(state["security"]),
                plans=pd.DataFrame(),
                retrieved_docs=pd.DataFrame(),
                keyword_docs=pd.DataFrame(),
                graph={},
                security=state["security"],
                trace=state["trace"],
            )
        for agent in [
            self.planner_agent,
            self.plan_search_agent,
            self.retrieval_agent,
            self.graph_agent,
            self.answer_agent,
        ]:
            state = agent.run(state)
        return AgentRun(
            question=question,
            answer=state["answer"],
            plans=state["plans"],
            retrieved_docs=pd.DataFrame(state["vector_results"]),
            keyword_docs=pd.DataFrame(state["keyword_results"]),
            graph=state["graph"],
            security=state["security"],
            trace=state["trace"],
        )

    def search_plans(self, filters: dict[str, Any] | None = None) -> pd.DataFrame:
        filters = filters or {}
        return self.copilot.search_plans(
            state=filters.get("state"),
            county=filters.get("county"),
            metal_level=filters.get("metal_level"),
            max_premium=filters.get("max_premium"),
        )

    def retrieve_terms(self, question: str) -> dict[str, list[dict[str, Any]]]:
        return {
            "vector_results": self.copilot.vector_search(question),
            "keyword_results": self.copilot.keyword_search(question),
        }

    def summarize_graph(self) -> dict[str, Any]:
        graph = build_knowledge_graph(self.copilot.plans_df)
        summary = graph_summary(graph)
        return {
            "nodes": summary.nodes,
            "edges": summary.edges,
            "top_relations": summary.top_relations,
        }
