import json
from importlib.resources import files
from typing import Any

from onboardflow.domain.models import EmployeeOnboardingInput


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


class JsonCatalogAdapter:
    def __init__(self, package: str = "onboardflow.catalogs") -> None:
        self.package = package

    def required_documents(self, employee: EmployeeOnboardingInput) -> list[dict[str, Any]]:
        rows = self._load("document_requirements.json")
        return [row for row in rows if self._applies(row.get("applies_to", []), employee)]

    def it_access_rules(self, employee: EmployeeOnboardingInput) -> list[dict[str, Any]]:
        rows = self._load("it_access_rules.json")
        return [row for row in rows if self._applies(row.get("departments", []), employee)]

    def training_items(self, employee: EmployeeOnboardingInput) -> list[dict[str, Any]]:
        rows = self._load("training_catalog.json")
        return [row for row in rows if self._applies(row.get("departments", []), employee)]

    def communication_templates(self) -> list[dict[str, Any]]:
        return self._load("communication_templates.json")

    def _load(self, name: str) -> list[dict[str, Any]]:
        resource = files(self.package).joinpath(name)
        return json.loads(resource.read_text(encoding="utf-8"))

    def _applies(self, values: list[str], employee: EmployeeOnboardingInput) -> bool:
        normalized = {_norm(value) for value in values}
        return "all" in normalized or _norm(employee.department) in normalized

