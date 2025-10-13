# Model Configuration Guide

This guide documents the current model lineup for the CrewAI blog generation flow and how to adjust it when performance tuning.

## Default Assignments

The backend now defaults to the following LiteLLM routes (see `backend/.env`):

- `RESEARCH_MODEL=gemini/gemini-2.5-flash-lite`
- `FACT_CHECK_MODEL=gemini/gemini-2.5-flash-lite`
- `CONTENT_MODEL=gemini/gemini-2.5-flash-lite`
- `FINALIZATION_MODEL=gemini/gemini-2.5-flash-lite`
- `DEFAULT_MODEL=gemini/gemini-2.5-flash-lite`
- `SUMMARY_MODEL=gemini/gemini-2.5-flash-lite`

All phases currently use `gemini-2.5-flash-lite`, which is the most reliable Gemini route available in this environment. Update this guide if access to higher-tier Gemini models is restored.

## Update Procedure

1. Copy `.env.example` (or the latest environment template) and populate provider API keys.
2. Verify the Gemini routes shown above are present in `backend/.env`.
3. Activate the backend virtual environment before running commands:
   ```bash
   cd backend
   source .venv/bin/activate
   ```
4. Restart backend services (`python src/main.py` or `make dev`) so CrewAI picks up the new environment variables.

## Rollback Strategy

If a regression surfaces after enabling the new Gemini stack, revert to the prior GPT-5 defaults by updating `backend/.env`:

```properties
CONTENT_MODEL=gpt-5-mini
FINALIZATION_MODEL=gpt-5-mini
RESEARCH_MODEL=gpt-5-mini
FACT_CHECK_MODEL=gpt-5-mini
DEFAULT_MODEL=gpt-5-nano
SUMMARY_MODEL=gpt-5-nano
```

Restart the backend after applying the rollback. Document any findings in the project changelog so the team can evaluate next steps.

## Validation Checklist

- [ ] End-to-end blog generation completes without model routing errors.
- [ ] Latency and cost metrics are within expected tolerances.
- [ ] Fact-checking output remains consistent with Phase 2 baselines.
- [ ] SSE streaming still delivers progress updates for every phase.

Complete this checklist before promoting the change beyond development.
