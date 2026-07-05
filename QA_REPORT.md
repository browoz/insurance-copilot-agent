# QA Report

Date: 2026-07-05

## Summary

Status: ready for demo/submission after recording review.

The app, backend tools, MCP server, and security behavior were tested as a capstone submission artifact. The main UI defects found from screenshots were fixed:

- State/county mismatch: the UI previously allowed `FL` with `Dallas`, while the question asked for Dallas, Texas.
- Dollar amount rendering: Streamlit interpreted `$1,000` style answer text as math markup, causing malformed display.

## Fixes Applied

- `app/streamlit_app.py`
  - County dropdown now depends on selected state.
  - Default demo path is `TX / Dallas / Silver`.
  - Invalid state/county pair is blocked.
  - Dollar signs in generated answers are escaped before Markdown rendering.

## Automated Checks

Commands:

```powershell
$env:PYTHONPATH=".\.deps;.\app"
python evaluation\run_eval.py
python scripts\smoke_mcp.py
```

Results:

- Evaluation: PASS 5 scenarios
- MCP smoke: PASS
- Browser UI QA: PASS

Browser UI checks:

- App title renders.
- Default state/county is TX/Dallas.
- Agent trace renders.
- Security decision renders.
- Structured plan results render.
- Knowledge graph relations render.
- Vector/RAG documents render.
- Malformed dollar/math text is absent.
- Prompt injection request is refused.

## Video Recommendation

Use screen capture / browser automation for the final capstone demo.

Reason:

- It proves the live product works.
- It shows the actual agent trace.
- It demonstrates the MCP/security story with evidence.
- It avoids the risk of a polished animation that does not prove functionality.

Do not use Remotion as the primary deliverable for this submission. Remotion is strong for marketing videos but unnecessary here.

Do not use HyperFrames as the primary proof video unless there is extra time. HyperFrames is useful for title cards and polished explainers, but the evaluator needs to see the working app.

Best format:

- Real app/browser demo
- Short generated title cards
- Narration
- Optional captions if time permits

## Generated QA Evidence

Screenshots were written under:

```text
output/insurance_copilot_submission/qa/
```

Demo video was written under:

```text
output/insurance_copilot_submission/video/
```

## Remaining Risks

- The implementation is ADK-style Python orchestration, not the official Google ADK runtime.
- Public hosted deployment is not yet verified.
- The generated narration is Windows SAPI, not Google TTS. It is acceptable for a proof video, but Google TTS or ElevenLabs would sound better if polish matters.
