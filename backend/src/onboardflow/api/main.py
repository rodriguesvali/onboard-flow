from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from onboardflow.api.dependencies import get_app_settings, get_application_service
from onboardflow.application.services import OnboardingApplicationService
from onboardflow.config.settings import Settings
from onboardflow.domain.models import (
    EmployeeOnboardingInput,
    RefinePlanRequest,
    RefinePlanResponse,
    RunStatusResponse,
    StartRunResponse,
)


def create_app() -> FastAPI:
    settings = get_app_settings()
    app = FastAPI(title="OnboardFlow AI Backend", version="0.1.0")
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

    return app


app = create_app()

