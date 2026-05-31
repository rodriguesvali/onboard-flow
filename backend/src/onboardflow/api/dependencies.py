from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from onboardflow.adapters.catalogs.json_catalog import JsonCatalogAdapter
from onboardflow.adapters.crewai.orchestrator import DeterministicOnboardingFlow
from onboardflow.adapters.markdown.renderer import MarkdownRenderer
from onboardflow.adapters.persistence.database import get_session
from onboardflow.adapters.persistence.repository import SqlAlchemyRunRepository
from onboardflow.application.services import OnboardingApplicationService
from onboardflow.config.settings import Settings, get_settings


def get_app_settings() -> Settings:
    return get_settings()


def get_application_service(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> Generator[OnboardingApplicationService, None, None]:
    catalog = JsonCatalogAdapter()
    repository = SqlAlchemyRunRepository(session)
    flow = DeterministicOnboardingFlow(catalog)
    renderer = MarkdownRenderer()
    yield OnboardingApplicationService(repository, flow, renderer, settings)

