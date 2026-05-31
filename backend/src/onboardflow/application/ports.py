from typing import Protocol

from onboardflow.domain.models import (
    EmployeeOnboardingInput,
    OnboardingPlanResult,
    OnboardingRun,
    SpecialistOutput,
    ValidationResult,
)


class CatalogPort(Protocol):
    def required_documents(self, employee: EmployeeOnboardingInput) -> list[dict]: ...

    def it_access_rules(self, employee: EmployeeOnboardingInput) -> list[dict]: ...

    def training_items(self, employee: EmployeeOnboardingInput) -> list[dict]: ...

    def communication_templates(self) -> list[dict]: ...


class RunRepositoryPort(Protocol):
    def save(self, run: OnboardingRun) -> None: ...

    def get(self, run_id: str) -> OnboardingRun | None: ...


class MarkdownRendererPort(Protocol):
    def render(self, plan: OnboardingPlanResult) -> str: ...


class OnboardingFlowPort(Protocol):
    def execute(
        self, run: OnboardingRun, employee: EmployeeOnboardingInput, validation: ValidationResult
    ) -> tuple[list[SpecialistOutput], OnboardingPlanResult]: ...

