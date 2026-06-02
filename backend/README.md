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
export ONBOARDFLOW_CREWAI_AMP_TRACING=false
uv run uvicorn onboardflow.api.main:app --reload --app-dir src --host 0.0.0.0 --port 8000
```

CrewAI output is normalized by the backend Flow before it is persisted or returned.

## CrewAI AMP observability

CrewAI AMP tracing is opt-in for this backend so local deterministic tests and demos remain provider-free and do not publish traces accidentally.

Before enabling tracing, authenticate the local environment with CrewAI AMP:

```bash
uv run crewai login
uv run crewai traces enable
uv run crewai traces status
```

Then enable live CrewAI mode and AMP tracing:

```bash
export ONBOARDFLOW_FLOW_MODE=crewai
export ONBOARDFLOW_CREWAI_AMP_TRACING=true
export CREWAI_TRACING_ENABLED=true
export GEMINI_API_KEY=...
uv run uvicorn onboardflow.api.main:app --reload --app-dir src --host 0.0.0.0 --port 8000
```

`ONBOARDFLOW_CREWAI_AMP_TRACING` maps to CrewAI's `tracing` flag on each `Crew` instance. The backend startup log prints `crewai_amp_tracing=<true|false>` with the active flow mode.
After startup, generate or refine an onboarding plan so the backend executes `Crew.kickoff()`. Startup alone does not publish a trace.
