# Insurance Copilot Agent MVP

Capstone prototype for a public-data health insurance copilot. The app helps a user search marketplace plans, compare structured plan facts, and get plain-English explanations through an ADK-style multi-agent RAG system.

## Problem Statement

Health insurance plan shopping is difficult because users must compare premiums, deductibles, out-of-pocket limits, metal levels, service areas, and benefit terminology at the same time. A normal chatbot can explain terms, but it can also hallucinate plan facts. A normal database search can filter plans, but it cannot explain insurance language.

This project combines both:

- Structured search for factual plan filtering
- RAG retrieval for insurance explanations
- LLM generation for beginner-friendly answers
- Knowledge graph links between plans, issuers, metal levels, service areas, and benefit concepts
- MCP tools for external agent/tool clients
- Security guardrails for prompt injection, private data, credentials, and regulated-advice requests

## Dataset Source

Primary dataset:

- CMS Marketplace Public Use Files, 2026
- Plan Attributes PUF
- Rate PUF
- Benefits and Cost Sharing PUF
- Service Area PUF

The project does not commit raw or processed CMS data. Teammates rebuild it locally using the scripts below.

## Architecture

```text
User question
  -> SecurityAgent: block private data, credentials, prompt injection, regulated advice
  -> PlannerAgent: choose structured search, RAG retrieval, graph, answer synthesis
  -> PlanSearchAgent: DuckDB SQL search over processed CMS plan facts
  -> RetrievalAgent: TF-IDF keyword retrieval + SVD vector retrieval
  -> KnowledgeGraphAgent: summarize plan/issuer/metal/service-area relationships
  -> AnswerSynthesisAgent: prompt builder + Mistral chat completion
  -> answer + agent trace + security decision + plan table + citations
```

## Tools

- Python for the app and data pipeline
- pandas for CMS CSV processing
- DuckDB for structured plan search
- scikit-learn TF-IDF for keyword retrieval
- scikit-learn TruncatedSVD for local semantic retrieval
- Mistral API for answer generation
- Streamlit for the UI
- networkx for the knowledge graph layer
- stdio JSON-RPC MCP server for tool exposure

## Setup

```powershell
cd "C:\Users\ravja\OneDrive\Documents\New project\insurance-copilot-local"
python -m pip install -r requirements.txt -t .deps
copy .env.example .env
```

Edit `.env`:

```env
MISTRAL_API_KEY=your_key_here
MISTRAL_BASE_URL=https://api.mistral.ai/v1/chat/completions
MISTRAL_MODEL=mistral-small-latest
```

Never commit `.env`.

## Build CMS Data

```powershell
$env:PYTHONPATH="C:\Users\ravja\OneDrive\Documents\New project\insurance-copilot-local\.deps"
python scripts\download_cms_pufs.py --year 2026 --datasets plan_attributes rates benefits service_areas
python scripts\build_cms_processed.py --year 2026 --sample-rows 250000
```

Use all rows when the MVP is stable:

```powershell
python scripts\build_cms_processed.py --year 2026 --sample-rows 0
```

Generated local files:

```text
data/processed/plans.csv
data/processed/benefits.csv
data/processed/service_areas.csv
data/processed/docs.csv
```

## Run CLI Smoke Test

```powershell
$env:PYTHONPATH="C:\Users\ravja\OneDrive\Documents\New project\insurance-copilot-local\.deps;C:\Users\ravja\OneDrive\Documents\New project\insurance-copilot-local\app"
python app\cli.py
```

The CLI prints the agent trace, answer, matching plans, and retrieved documents.

## Run Streamlit UI

```powershell
$env:PYTHONPATH="C:\Users\ravja\OneDrive\Documents\New project\insurance-copilot-local\.deps;C:\Users\ravja\OneDrive\Documents\New project\insurance-copilot-local\app"
python -m streamlit run app\streamlit_app.py --global.developmentMode false --server.address 127.0.0.1 --server.port 8501
```

The UI shows:

- plan and graph metrics
- filters
- agent trace
- security decision
- answer
- structured plan table
- retrieved documents

## Run Evaluation

```powershell
$env:PYTHONPATH="C:\Users\ravja\OneDrive\Documents\New project\insurance-copilot-local\.deps;C:\Users\ravja\OneDrive\Documents\New project\insurance-copilot-local\app"
python evaluation\run_eval.py
```

The evaluation checks:

- structured plan search returns results
- retrieval finds deductible documentation
- agent trace includes plan search and retrieval agents
- prompt injection is blocked
- private client/policy data requests are blocked
- graph summary is non-empty

## Run MCP Server Smoke Test

```powershell
$env:PYTHONPATH="C:\Users\ravja\OneDrive\Documents\New project\insurance-copilot-local\.deps;C:\Users\ravja\OneDrive\Documents\New project\insurance-copilot-local\app"
python scripts\smoke_mcp.py
```

MCP tools exposed by `mcp_server.py`:

- `search_plans`
- `retrieve_terms`
- `summarize_graph`
- `answer_question`

## Docker

```powershell
docker build -t insurance-copilot .
docker run --rm -p 8501:8501 --env MISTRAL_API_KEY=$env:MISTRAL_API_KEY insurance-copilot
```

## RAG Design

The app intentionally separates facts from explanations.

Structured facts use DuckDB:

- State
- County/service area
- Metal level
- Monthly premium
- Deductible options
- Out-of-pocket maximum options

Explanations use retrieval:

- What deductible means
- What premium means
- What metal level means
- What CMS PUF files contain

The LLM receives both sources and is instructed not to invent missing plan details.

## Knowledge Graph Layer

The first graph version models:

- Plan -> Issuer
- Plan -> Metal Level
- Plan -> State
- Plan -> Service Area
- Plan -> Deductible Options
- Plan -> Out-of-Pocket Maximum Options

The graph is built from `plans.csv` in `app/knowledge_graph.py`. It uses `networkx` when installed and falls back to a small local graph class if not.

## Current Limitations

- County matching currently supports only a small built-in county-to-FIPS mapping.
- Deductible and out-of-pocket values can vary by plan variant/CSR level, so the app shows options rather than one guaranteed value.
- Premium uses age-40 rates as a simple comparable estimate.
- This is not financial, legal, or medical advice.
- The current retrieval corpus is small; more official CMS and glossary documents should be added.
- The multi-agent layer is ADK-style and explicit in Python. If a submission requires the official Google ADK runtime, add that wrapper as a final integration layer.

## Future Improvements

- Add full county-name-to-FIPS lookup.
- Add plan variant and CSR-level selection.
- Add richer official insurance glossary documents.
- Add evaluation questions and expected answers.
- Add automated tests for data processing and search filters.
- Replace local vector retrieval with a persistent vector database if the document corpus becomes large.
