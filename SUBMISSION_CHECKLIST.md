# Submission Checklist

## Current Rubric Mapping

| Rubric item | Evidence in project | Status |
|---|---|---|
| Agent / multi-agent system / ADK | `app/agents.py` implements explicit ADK-style agents: security, planner, plan search, retrieval, graph, answer synthesis | Ready |
| MCP Server | `mcp_server.py` exposes `search_plans`, `retrieve_terms`, `summarize_graph`, and `answer_question` over stdio JSON-RPC | Ready |
| Antigravity | `DEMO_SCRIPT.md` gives exact recording path and proof points | Needs recording |
| Security features | `app/security.py` blocks prompt injection, private-data requests, credentials, client identifiers, and regulated advice requests | Ready |
| Deployability | `Dockerfile`, Streamlit run command, README instructions | Ready locally; hosted URL optional |
| Agent skills | MCP tools plus agent classes demonstrate callable skills/tools | Ready |

## Final Submission Files

Submit:
- `README.md`
- `SUBMISSION_CHECKLIST.md`
- `SUBMISSION_EXECUTION_LOOP.md`
- `DEMO_SCRIPT.md`
- `Dockerfile`
- `requirements.txt`
- `app/`
- `evaluation/`
- `scripts/`
- `mcp_server.py`
- `data/sample/`
- Kaggle notebook if required: `../insurance-kaggle-notebook/insurance_copilot_rag_mvp.ipynb`

Do not submit:
- `.env`
- `.deps/`
- `data/raw/`
- `data/processed/`
- `__pycache__/`
- any private brokerage/client document folders

## Verification Commands

```powershell
$env:PYTHONPATH=".\.deps;.\app"
python evaluation\run_eval.py
python scripts\smoke_mcp.py
python app\cli.py
python -m streamlit run app\streamlit_app.py
```

## Known Limitations To State Honestly

- This is an educational copilot, not regulated advice.
- The local semantic retriever uses TF-IDF plus SVD, not transformer embeddings, to keep the project reproducible.
- County matching is limited to a small built-in map for demo states/counties.
- CMS rate display uses age-40 rates as a comparable estimate.
- The hosted deployment is optional unless the event explicitly requires a public URL.
