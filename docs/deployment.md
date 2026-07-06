# Deployment

## Local Streamlit

```powershell
git clone https://github.com/browoz/insurance-copilot-agent.git
cd insurance-copilot-agent
python -m pip install -r requirements.txt -t .deps
$env:PYTHONPATH=".\.deps;.\app"
python -m streamlit run app\streamlit_app.py --global.developmentMode false --server.address 127.0.0.1 --server.port 8501
```

## Docker

```powershell
docker build -t insurance-copilot .
docker run --rm -p 8501:8501 --env MISTRAL_API_KEY=$env:MISTRAL_API_KEY insurance-copilot
```

## MCP Server

```powershell
$env:PYTHONPATH=".\.deps;.\app"
python mcp_server.py
```

The server uses stdio JSON-RPC and exposes:
- `search_plans`
- `retrieve_terms`
- `summarize_graph`
- `answer_question`

## Secret Handling

Use environment variables or `.env` locally:

```env
MISTRAL_API_KEY=...
MISTRAL_BASE_URL=https://api.mistral.ai/v1/chat/completions
MISTRAL_MODEL=mistral-small-latest
```

Do not commit `.env`, local dependency folders, raw CMS downloads, processed CMS data, or private brokerage documents.
