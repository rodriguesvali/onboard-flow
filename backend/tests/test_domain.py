from onboardflow.domain.models import EmployeeOnboardingInput


def test_employee_input_accepts_frontend_camel_case(employee_payload):
    employee = EmployeeOnboardingInput.model_validate(employee_payload)

    assert employee.full_name == "Ana Silva"
    assert employee.direct_manager == "Joaquim"
    assert employee.model_dump(mode="json", by_alias=True)["fullName"] == "Ana Silva"


def test_crewai_model_name_prefixes_gemini_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "google-gemini")
    monkeypatch.setenv("LLM_PROFILE_DEFAULT_MODEL", "gemini-2.0-flash")

    from onboardflow.config.settings import get_settings

    get_settings.cache_clear()
    try:
        assert get_settings().crewai_model_name() == "gemini/gemini-2.0-flash"
    finally:
        get_settings.cache_clear()

def test_crewai_model_name_preserves_explicit_provider_prefix(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "google-gemini")
    monkeypatch.setenv("LLM_PROFILE_DEFAULT_MODEL", "openai/gemini-2.0-flash")

    from onboardflow.config.settings import get_settings

    get_settings.cache_clear()
    try:
        assert get_settings().crewai_model_name() == "openai/gemini-2.0-flash"
    finally:
        get_settings.cache_clear()


def test_flow_mode_accepts_onboardflow_env_alias(monkeypatch):
    monkeypatch.setenv("ONBOARDFLOW_FLOW_MODE", "crewai")

    from onboardflow.config.settings import get_settings

    get_settings.cache_clear()
    try:
        assert get_settings().onboarding_flow_mode == "crewai"
    finally:
        get_settings.cache_clear()
