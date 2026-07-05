from __future__ import annotations

import json
import sys
from typing import Any

from app.agents import InsuranceAgentSystem


SERVER_INFO = {"name": "insurance-copilot-mcp", "version": "0.1.0"}


def json_default(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict(orient="records")
    return str(value)


class InsuranceMcpServer:
    """Minimal MCP-compatible stdio JSON-RPC server for demo and rubric proof."""

    def __init__(self) -> None:
        self.agent_system = InsuranceAgentSystem()

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        request_id = request.get("id")
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": SERVER_INFO,
                    "capabilities": {"tools": {}},
                }
            elif method == "notifications/initialized":
                return None
            elif method == "tools/list":
                result = {"tools": self.tools()}
            elif method == "tools/call":
                params = request.get("params") or {}
                result = self.call_tool(params.get("name"), params.get("arguments") or {})
            else:
                return self.error(request_id, -32601, f"Unsupported method: {method}")
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as exc:
            return self.error(request_id, -32000, f"{type(exc).__name__}: {exc}")

    @staticmethod
    def error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    @staticmethod
    def tools() -> list[dict[str, Any]]:
        return [
            {
                "name": "search_plans",
                "description": "Search public CMS Marketplace plans by state, county, metal level, and max premium.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "state": {"type": "string"},
                        "county": {"type": "string"},
                        "metal_level": {"type": "string"},
                        "max_premium": {"type": "number"},
                    },
                },
            },
            {
                "name": "retrieve_terms",
                "description": "Retrieve public insurance glossary/CMS explanation documents for a question.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"question": {"type": "string"}},
                    "required": ["question"],
                },
            },
            {
                "name": "summarize_graph",
                "description": "Return knowledge graph node, edge, and relation counts.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "answer_question",
                "description": "Run the ADK-style insurance agent system and return answer, plans, docs, graph, and trace.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "filters": {"type": "object"},
                    },
                    "required": ["question"],
                },
            },
        ]

    def content(self, payload: Any) -> dict[str, Any]:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, default=json_default, indent=2),
                }
            ]
        }

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "search_plans":
            plans = self.agent_system.search_plans(arguments)
            return self.content({"plans": plans.head(25), "count": len(plans)})
        if name == "retrieve_terms":
            return self.content(self.agent_system.retrieve_terms(arguments["question"]))
        if name == "summarize_graph":
            return self.content(self.agent_system.summarize_graph())
        if name == "answer_question":
            run = self.agent_system.ask(arguments["question"], arguments.get("filters") or {})
            return self.content(
                {
                    "answer": run.answer,
                    "plans": run.plans.head(15),
                    "retrieved_docs": run.retrieved_docs,
                    "keyword_docs": run.keyword_docs,
                    "graph": run.graph,
                    "security_allowed": run.security.allowed,
                    "security_reason": run.security.reason,
                    "trace": [step.__dict__ for step in run.trace],
                }
            )
        raise ValueError(f"Unknown tool: {name}")


def main() -> int:
    server = InsuranceMcpServer()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        response = server.handle(json.loads(line))
        if response is not None:
            print(json.dumps(response, default=json_default), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
