from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./onboardflow.db"
    api_cors_origins: str = "http://localhost:4200,http://127.0.0.1:4200"
    mock_hr_user_id: str = "mock-hr-user"
    mock_hr_user_name: str = "Mock HR User"
    onboarding_flow_mode: Literal["deterministic", "crewai"] = Field(
        default="deterministic",
        validation_alias=AliasChoices("ONBOARDING_FLOW_MODE", "ONBOARDFLOW_FLOW_MODE"),
    )
    crewai_verbose: bool = False
    crewai_temperature: float = 0.2
    llm_provider: str = "google-gemini"
    llm_model: str = "gemini-3.5-flash"
    llm_profile_default_model: str = Field(default="gemini-3.5-flash")
    llm_profile_reasoning_model: str = Field(default="gemini-3.5-flash")
    llm_profile_efficient_model: str = Field(default="gemini-3.5-flash")
    llm_profile_creative_model: str = Field(default="gemini-3.5-flash")
    llm_profile_tool_calling_model: str = Field(default="gemini-3.5-flash")
    llm_profile_refinement_model: str = Field(default="gemini-3.5-flash")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]

    def model_profile_map(self) -> dict[str, str]:
        return {
            "default": self.llm_profile_default_model,
            "reasoning": self.llm_profile_reasoning_model,
            "efficient": self.llm_profile_efficient_model,
            "creative": self.llm_profile_creative_model,
            "tool_calling": self.llm_profile_tool_calling_model,
            "refinement": self.llm_profile_refinement_model,
        }

    def crewai_model_name(self, profile: str = "default") -> str:
        model = self.model_profile_map().get(profile, self.llm_model)
        if "/" in model:
            return model
        if self.llm_provider == "google-gemini":
            return f"gemini/{model}"
        return model


@lru_cache
def get_settings() -> Settings:
    return Settings()
