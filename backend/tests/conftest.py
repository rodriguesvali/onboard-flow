import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    os.environ["DATABASE_URL"] = database_url
    os.environ["ONBOARDFLOW_FLOW_MODE"] = "deterministic"

    from onboardflow.config.settings import get_settings

    get_settings.cache_clear()

    from onboardflow.adapters.persistence.database import Base, get_session, make_engine
    from onboardflow.api.main import create_app

    engine = make_engine(database_url)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_session():
        with TestingSessionLocal() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def employee_payload() -> dict:
    return {
        "fullName": "Ana Silva",
        "email": "ana.silva@example.com",
        "role": "Engenheira de Software",
        "department": "Engenharia",
        "directManager": "Joaquim",
        "startDate": "2026-06-15",
        "employmentType": "Tempo integral",
        "workMode": "Remoto",
        "seniority": "Pleno",
        "location": "",
        "contractRegion": "BR",
        "preferredLanguage": "pt-BR",
        "equipmentNeeds": "Notebook",
        "specialAccessNotes": "",
    }

