from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
SAMPLE_DIR = ROOT / "data" / "sample"


@dataclass(frozen=True)
class GraphSummary:
    nodes: int
    edges: int
    top_relations: dict[str, int]


class SimpleGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[tuple[str, str, dict[str, Any]]] = []
        self.neighbors: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)

    def add_node(self, node_id: str, **attrs: Any) -> None:
        self.nodes.setdefault(node_id, {}).update(attrs)

    def add_edge(self, source: str, target: str, **attrs: Any) -> None:
        self.edges.append((source, target, attrs))
        self.neighbors[source].append((target, attrs))

    def number_of_nodes(self) -> int:
        return len(self.nodes)

    def number_of_edges(self) -> int:
        return len(self.edges)


def default_path(filename: str) -> Path:
    processed = PROCESSED_DIR / filename
    if processed.exists():
        return processed
    return SAMPLE_DIR / filename


def build_knowledge_graph(plans: pd.DataFrame | None = None) -> Any:
    if plans is None:
        plans = pd.read_csv(default_path("plans.csv"))

    try:
        import networkx as nx

        graph: Any = nx.MultiDiGraph()
    except ImportError:
        graph = SimpleGraph()

    for _, row in plans.iterrows():
        plan_id = str(row.get("plan_id", "")).strip()
        if not plan_id:
            continue

        plan_node = f"plan:{plan_id}"
        graph.add_node(
            plan_node,
            type="plan",
            plan_id=plan_id,
            name=row.get("plan_name", ""),
            premium=row.get("monthly_premium", ""),
            deductible=row.get("deductible", ""),
            out_of_pocket_max=row.get("out_of_pocket_max", ""),
        )

        relationships = [
            ("issuer", row.get("issuer", ""), "OFFERED_BY"),
            ("metal_level", row.get("metal_level", ""), "HAS_METAL_LEVEL"),
            ("state", row.get("state", ""), "AVAILABLE_IN_STATE"),
            ("service_area", row.get("service_area_id", ""), "USES_SERVICE_AREA"),
            ("benefit", row.get("deductible", ""), "HAS_DEDUCTIBLE_OPTIONS"),
            ("benefit", row.get("out_of_pocket_max", ""), "HAS_OOP_MAX_OPTIONS"),
        ]
        for node_type, value, relation in relationships:
            value_text = "" if pd.isna(value) else str(value).strip()
            if not value_text:
                continue
            target = f"{node_type}:{value_text}"
            graph.add_node(target, type=node_type, name=value_text)
            graph.add_edge(plan_node, target, relation=relation)

    return graph


def graph_summary(graph: Any) -> GraphSummary:
    relation_counts: dict[str, int] = defaultdict(int)
    edges = graph.edges(data=True) if hasattr(graph, "edges") and callable(graph.edges) else graph.edges
    for edge in edges:
        attrs = edge[-1]
        relation_counts[str(attrs.get("relation", "RELATED_TO"))] += 1
    return GraphSummary(
        nodes=graph.number_of_nodes(),
        edges=graph.number_of_edges(),
        top_relations=dict(sorted(relation_counts.items(), key=lambda item: item[1], reverse=True)),
    )


if __name__ == "__main__":
    summary = graph_summary(build_knowledge_graph())
    print(f"nodes={summary.nodes:,}")
    print(f"edges={summary.edges:,}")
    for relation, count in summary.top_relations.items():
        print(f"{relation}: {count:,}")
