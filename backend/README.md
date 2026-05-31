# OnboardFlow Backend

Python backend for the OnboardFlow AI MVP.

## Commands

```bash
uv sync
uv run alembic upgrade head
uv run pytest
uv run uvicorn onboardflow.api.main:app --reload --host 0.0.0.0 --port 8000
```

## API

- `POST /api/onboarding/generate`
- `GET /api/onboarding/runs/{runId}`
- `POST /api/onboarding/runs/{runId}/refine`

The service returns structured JSON as the primary contract and Markdown as a rendered view.

