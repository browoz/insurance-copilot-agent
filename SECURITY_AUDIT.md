# Security Audit Before Public Upload

Date: 2026-07-05

## Result

Ready for public GitHub upload after using the sanitized upload folder.

## What Was Checked

- Secret scan across publishable project files.
- Exclusion check for local environment files, dependency folders, raw data, processed data, generated caches, and private brokerage paths.
- Safety review for prompt injection, private document requests, credentials, client identifiers, and regulated advice requests.
- Evaluation and MCP smoke tests.

## Findings

- No real API keys were found in the publishable files.
- `.env` contains a real local Mistral key and must not be committed.
- `.gitignore` excludes `.env`, `.deps`, raw CMS data, processed CMS data, caches, logs, local secrets, and Kaggle credentials.
- The app uses public CMS sample data for public repository usage.
- The app explicitly blocks private brokerage/client document requests.
- No private brokerage/client document folders are included.

## Files Excluded From Public Upload

- `.env`
- `.deps/`
- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `data/raw/`
- `data/processed/`
- local logs
- local secrets
- private brokerage documents

## Verification Commands

```powershell
$env:PYTHONPATH=".\.deps;.\app"
python evaluation\run_eval.py
python scripts\smoke_mcp.py
python -m py_compile app\rag_pipeline.py scripts\gemini_tts.py
```

Latest result:

```text
PASS 5 evaluation scenarios
MCP smoke passed: ok id=1 through ok id=4
Python compile passed
```

## Required Follow-Up

Rotate the local Mistral API key after submission because it exists in `.env` on this machine.
