import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from onboardflow.api.dependencies import get_app_settings, get_application_service
from onboardflow.application.services import OnboardingApplicationService
from onboardflow.config.settings import Settings
from onboardflow.domain.models import (
    DispatchRunResponse,
    EmployeeOnboardingInput,
    RefinePlanRequest,
    RefinePlanResponse,
    RunStatusResponse,
    StartRunResponse,
)

logger = logging.getLogger("uvicorn.error")


def create_app() -> FastAPI:
    settings = get_app_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            "onboardflow_backend_started flow_mode=%s crewai_amp_tracing=%s",
            settings.onboarding_flow_mode,
            settings.crewai_amp_tracing_enabled,
        )
        yield

    app = FastAPI(title="OnboardFlow AI Backend", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/onboarding/generate", response_model=StartRunResponse)
    def generate_onboarding_plan(
        payload: EmployeeOnboardingInput,
        service: OnboardingApplicationService = Depends(get_application_service),
    ) -> StartRunResponse:
        return service.generate(payload)

    @app.get("/api/onboarding/runs/{run_id}", response_model=RunStatusResponse)
    def get_run(
        run_id: str,
        service: OnboardingApplicationService = Depends(get_application_service),
    ) -> RunStatusResponse:
        response = service.get_run(run_id)
        if response is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return response

    @app.post("/api/onboarding/runs/{run_id}/refine", response_model=RefinePlanResponse)
    def refine_run(
        run_id: str,
        payload: RefinePlanRequest,
        service: OnboardingApplicationService = Depends(get_application_service),
    ) -> RefinePlanResponse:
        response = service.refine(run_id, payload)
        if response is None:
            raise HTTPException(status_code=404, detail="Run not found or not ready for refinement")
        return response

    @app.post("/api/onboarding/runs/{run_id}/dispatch", response_model=DispatchRunResponse)
    def dispatch_run(
        run_id: str,
        service: OnboardingApplicationService = Depends(get_application_service),
    ) -> DispatchRunResponse:
        response = service.dispatch(run_id)
        if response is None:
            raise HTTPException(status_code=404, detail="Run not found or not ready for dispatch")
        return response

    return app


app = create_app()
