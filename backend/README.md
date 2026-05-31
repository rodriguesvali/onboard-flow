# OnboardFlow Backend

Python backend for the OnboardFlow AI MVP.

## Commands

```bash
uv sync
uv run alembic upgrade head
uv run pytest
uv run uvicorn onboardflow.api.main:app --reload --app-dir src --host 0.0.0.0 --port 8000
```

## API

- `POST /api/onboarding/generate`
- `GET /api/onboarding/runs/{runId}`
- `POST /api/onboarding/runs/{runId}/refine`

The service returns structured JSON as the primary contract and Markdown as a rendered view.


## CrewAI execution

The default `ONBOARDFLOW_FLOW_MODE=deterministic` keeps local tests and demos provider-free.
To run the real CrewAI specialist tasks, install extras and provide Gemini credentials. The CrewAI Google GenAI extra is required for native Gemini execution:

```bash
uv sync --all-extras --dev
export ONBOARDFLOW_FLOW_MODE=crewai
export GEMINI_API_KEY=...
export CREWAI_TRACING_ENABLED=false
uv run uvicorn onboardflow.api.main:app --reload --app-dir src --host 0.0.0.0 --port 8000
```

CrewAI output is normalized by the backend Flow before it is persisted or returned.
