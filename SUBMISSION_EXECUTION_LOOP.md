# Submission Execution Loop

Assumption: submission deadline is July 6, 2026. I could not verify the official deadline from public search using the available rubric terms, so treat this as a hard deadline until the event link confirms otherwise.

## Success Target

Move the project from a working RAG MVP to a rubric-aligned agentic insurance copilot.

Target readiness: 90%+

Rubric coverage:
- Agent / multi-agent system using ADK or an ADK-compatible structure
- MCP server
- Antigravity demo/video evidence
- Security features
- Deployability
- Agent skills

## Resource Budget

Conservative token budget: 120k-160k tokens.

Minimum viable sprint:
- 70k-90k tokens
- 6-8 focused hours
- One user decision: confirm whether Google ADK is mandatory
- One user resource: valid LLM key for demo, if live generation is required

Strong submission sprint:
- 120k-160k tokens
- 10-14 focused hours
- Deployment target access
- Final video recording time

## Deadline Strategy

Because the deadline is close, the project should not pivot to a new Kaggle ML project. The current RAG/copilot project already has working data, retrieval, graph, Streamlit, and LLM pieces. The fastest success path is wrapping it into the required agent/MCP/demo structure.

## Execution Loops

Each loop ends with a concrete artifact and a pass/fail gate.

### Loop 1: Rubric Audit

Deliverables:
- `SUBMISSION_CHECKLIST.md`
- rubric mapping table
- missing-work list

Gate:
- Every rubric item has a code/video/documentation proof target.

### Loop 2: Agent Layer

Deliverables:
- `app/agents.py`
- planner agent
- plan search agent
- retrieval agent
- answer synthesis agent

Gate:
- The app can show agent steps before final answer.

### Loop 3: ADK Decision

If Google ADK is mandatory:
- add minimal ADK agent wrapper
- document setup and run command

If normal Python multi-agent is acceptable:
- keep lightweight local agent classes
- make behavior explicit in code and video

Gate:
- Rubric line `Agent / Multi-agent system (ADK)` is defensible.

### Loop 4: MCP Server

Deliverables:
- `mcp_server.py`
- tools:
  - `search_plans`
  - `retrieve_terms`
  - `summarize_graph`
  - `answer_question`

Gate:
- MCP tools can be called locally and shown in the demo.

### Loop 5: Security Features

Deliverables:
- prompt injection guard
- public-data-only guard
- source-only answer policy
- no medical/legal/financial advice disclaimer
- secret handling docs

Gate:
- Demo includes a blocked unsafe/private-data request.

### Loop 6: Evaluation

Deliverables:
- `evaluation/questions.json`
- `evaluation/run_eval.py`
- pass/fail checks for:
  - plan search
  - retrieval citation
  - no hallucinated plan facts
  - security refusal

Gate:
- Evaluation script runs locally.

### Loop 7: Deployability

Deliverables:
- clean run instructions
- `Dockerfile` or Streamlit deployment instructions
- `.env.example`
- deployment checklist

Gate:
- Project runs from clean setup instructions.

### Loop 8: Kaggle / Notebook Cleanup

Deliverables:
- final notebook or notebook export
- no private data
- no local absolute paths
- public-data explanation

Gate:
- Notebook can be uploaded without secrets or private files.

### Loop 9: Demo Package

Deliverables:
- `DEMO_SCRIPT.md`
- 3-5 minute video script
- exact commands to run
- rubric proof checklist

Gate:
- User can record the video without improvising.

### Loop 10: Final Submission Audit

Deliverables:
- final file list
- do-not-submit file list
- final risk list

Gate:
- Submission package is ready.

## Minimum Submission Cut

If time collapses, prioritize:
1. agent layer
2. MCP server
3. security guardrails
4. demo script
5. README/checklist

Defer:
- advanced deployment
- model tuning
- large UI redesign
- full CMS data rebuild

## Current Known Risks

- The existing app is a RAG MVP, not yet clearly an ADK/MCP agent project.
- No MCP server exists yet.
- No tests/evaluation were found.
- No deployment proof was found.
- `.env` exists locally and must not be submitted.
- Processed/raw CMS data is gitignored; this is good for repository hygiene, but the submission must explain how to rebuild or provide Kaggle-safe sample data.
