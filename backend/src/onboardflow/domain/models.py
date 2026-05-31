from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class RunStatus(StrEnum):
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class PlanStatus(StrEnum):
    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"
    INCOMPLETE = "incomplete"


class ItemStatus(StrEnum):
    PENDING = "pending"
    RECOMMENDED = "recommended"
    BLOCKED = "blocked"
    DONE = "done"


class EmployeeOnboardingInput(CamelModel):
    full_name: str = Field(alias="fullName", min_length=1)
    email: EmailStr
    role: str = Field(min_length=1)
    department: str = Field(min_length=1)
    direct_manager: str = Field(alias="directManager", min_length=1)
    start_date: date = Field(alias="startDate")
    employment_type: str = Field(alias="employmentType", min_length=1)
    work_mode: str = Field(alias="workMode", min_length=1)
    seniority: str | None = None
    location: str | None = None
    contract_region: str | None = Field(default=None, alias="contractRegion")
    preferred_language: str | None = Field(default=None, alias="preferredLanguage")
    equipment_needs: str | None = Field(default=None, alias="equipmentNeeds")
    special_access_notes: str | None = Field(default=None, alias="specialAccessNotes")

    @field_validator("*", mode="before")
    @classmethod
    def blank_strings_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class ValidationIssue(CamelModel):
    field: str
    message: str
    severity: Literal["error", "warning"]


class ValidationResult(CamelModel):
    status: Literal["complete", "draft_usable", "unusable"]
    issues: list[ValidationIssue] = Field(default_factory=list)


class EmployeeProfile(CamelModel):
    full_name: str = Field(alias="fullName")
    role: str
    department: str
    direct_manager: str = Field(alias="directManager")
    start_date: str = Field(alias="startDate")
    work_mode: str = Field(alias="workMode")


class ResultItem(CamelModel):
    title: str
    owner_role: str = Field(alias="ownerRole")
    status: ItemStatus
    rationale: str | None = None


class CommunicationDraft(CamelModel):
    audience: Literal["collaborator", "manager", "it", "hr"]
    subject: str
    body: str
    draft: Literal[True] = True


class OnboardingPlanResult(CamelModel):
    employee_profile: EmployeeProfile = Field(alias="employeeProfile")
    executive_summary: str = Field(alias="executiveSummary")
    required_documents: list[ResultItem] = Field(alias="requiredDocuments")
    it_checklist: list[ResultItem] = Field(alias="itChecklist")
    training_path: list[ResultItem] = Field(alias="trainingPath")
    initial_agenda: list[ResultItem] = Field(alias="initialAgenda")
    communications: list[CommunicationDraft]
    pending_actions: list[ResultItem] = Field(alias="pendingActions")
    risk_flags: list[ResultItem] = Field(alias="riskFlags")
    status: PlanStatus
    next_recommended_actions: list[str] = Field(alias="nextRecommendedActions")


class AgentAction(CamelModel):
    action_id: str = Field(default_factory=lambda: new_id("action"), alias="actionId")
    run_id: str = Field(alias="runId")
    actor_id: str = Field(alias="actorId")
    actor_name: str = Field(alias="actorName")
    action_type: str = Field(alias="actionType")
    task_id: str | None = Field(default=None, alias="taskId")
    agent_name: str | None = Field(default=None, alias="agentName")
    status: str
    summary: str
    model_provider: str | None = Field(default=None, alias="modelProvider")
    model_name: str | None = Field(default=None, alias="modelName")
    model_profile: str | None = Field(default=None, alias="modelProfile")
    retry_count: int = Field(default=0, alias="retryCount")
    validation_result: str | None = Field(default=None, alias="validationResult")
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")


class SpecialistOutput(CamelModel):
    task_id: str = Field(alias="taskId")
    agent_name: str = Field(alias="agentName")
    status: Literal["done", "incomplete"]
    summary: str
    items: list[ResultItem] = Field(default_factory=list)
    pending_actions: list[ResultItem] = Field(default_factory=list, alias="pendingActions")
    risks: list[ResultItem] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    input_sources: list[str] = Field(default_factory=list, alias="inputSources")
    quality_checks: list[str] = Field(default_factory=list, alias="qualityChecks")


class OnboardingRun(CamelModel):
    run_id: str = Field(default_factory=lambda: new_id("run"), alias="runId")
    status: RunStatus = RunStatus.RUNNING
    message: str = "Run criado."
    input_data: dict[str, Any] = Field(default_factory=dict, alias="inputData")
    validation_result: ValidationResult | None = Field(default=None, alias="validationResult")
    result: OnboardingPlanResult | None = None
    markdown: str | None = None
    error_message: str | None = Field(default=None, alias="errorMessage")
    action_history: list[AgentAction] = Field(default_factory=list, alias="actionHistory")
    revision_number: int = Field(default=1, alias="revisionNumber")
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")
    updated_at: datetime = Field(default_factory=utc_now, alias="updatedAt")


class StartRunResponse(CamelModel):
    run_id: str = Field(alias="runId")
    status: Literal["running"]


class RunStatusResponse(CamelModel):
    run_id: str = Field(alias="runId")
    status: RunStatus
    message: str
    result: OnboardingPlanResult | None = None
    markdown: str | None = None
    validation_result: ValidationResult | None = Field(default=None, alias="validationResult")
    agent_activity: list[AgentAction] = Field(default_factory=list, alias="agentActivity")
    error_message: str | None = Field(default=None, alias="errorMessage")


class RefinePlanRequest(CamelModel):
    instruction: str = Field(min_length=1)
    plan_version: int | None = Field(default=None, alias="planVersion")


class RefinePlanResponse(CamelModel):
    run_id: str = Field(alias="runId")
    status: RunStatus
    revision_id: str = Field(alias="revisionId")
    revision_number: int = Field(alias="revisionNumber")
    result: OnboardingPlanResult
    markdown: str
    validation_result: ValidationResult = Field(alias="validationResult")

