from dataclasses import dataclass

from onboardflow.application.ports import MarkdownRendererPort, OnboardingFlowPort, RunRepositoryPort
from onboardflow.config.settings import Settings
from onboardflow.domain.models import (
    AgentAction,
    EmployeeOnboardingInput,
    ItemStatus,
    OnboardingPlanResult,
    OnboardingRun,
    PlanStatus,
    RefinePlanRequest,
    RefinePlanResponse,
    ResultItem,
    RunStatus,
    RunStatusResponse,
    StartRunResponse,
    ValidationIssue,
    ValidationResult,
    new_id,
    utc_now,
)


def validate_employee_input(employee: EmployeeOnboardingInput) -> ValidationResult:
    issues: list[ValidationIssue] = []
    if employee.start_date.isoformat() < "2026-01-01":
        issues.append(
            ValidationIssue(field="startDate", message="Data de inicio parece invalida.", severity="error")
        )
    if employee.work_mode.lower() == "presencial" and not employee.location:
        issues.append(
            ValidationIssue(
                field="location",
                message="Localidade deve ser confirmada para trabalho presencial.",
                severity="warning",
            )
        )
    if issues and any(issue.severity == "error" for issue in issues):
        return ValidationResult(status="unusable", issues=issues)
    if issues:
        return ValidationResult(status="draft_usable", issues=issues)
    return ValidationResult(status="complete")


@dataclass
class ActorContext:
    actor_id: str
    actor_name: str


class OnboardingApplicationService:
    def __init__(
        self,
        repository: RunRepositoryPort,
        flow: OnboardingFlowPort,
        markdown_renderer: MarkdownRendererPort,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.flow = flow
        self.markdown_renderer = markdown_renderer
        self.settings = settings
        self.actor = ActorContext(settings.mock_hr_user_id, settings.mock_hr_user_name)

    def generate(self, employee: EmployeeOnboardingInput) -> StartRunResponse:
        run = OnboardingRun(inputData=employee.model_dump(mode="json", by_alias=True))
        run.action_history.append(self._action(run.run_id, "generation_requested", "Run recebido."))
        self.repository.save(run)

        validation = validate_employee_input(employee)
        run.validation_result = validation
        run.action_history.append(
            self._action(
                run.run_id,
                "input_validated",
                f"Validacao concluida com status {validation.status}.",
                validation_result=validation.status,
            )
        )

        if validation.status == "unusable":
            run.status = RunStatus.ERROR
            run.message = "Nao foi possivel gerar o plano de onboarding."
            run.error_message = "Entrada invalida para execucao dos agentes."
            run.updated_at = utc_now()
            self.repository.save(run)
            return StartRunResponse(runId=run.run_id, status="running")

        specialist_outputs, plan = self.flow.execute(run, employee, validation)
        for output in specialist_outputs:
            run.action_history.append(
                self._action(
                    run.run_id,
                    "specialist_task_completed",
                    output.summary,
                    task_id=output.task_id,
                    agent_name=output.agent_name,
                    model_profile=self._profile_for(output.task_id),
                    validation_result=output.status,
                )
            )

        run.result = plan
        run.markdown = self.markdown_renderer.render(plan)
        run.status = RunStatus.DONE
        run.message = "Plano de onboarding gerado para revisao humana."
        run.updated_at = utc_now()
        run.action_history.append(self._action(run.run_id, "plan_normalized", "Plano JSON validado."))
        self.repository.save(run)
        return StartRunResponse(runId=run.run_id, status="running")

    def get_run(self, run_id: str) -> RunStatusResponse | None:
        run = self.repository.get(run_id)
        if run is None:
            return None
        return RunStatusResponse(
            runId=run.run_id,
            status=run.status,
            message=run.message,
            result=run.result,
            markdown=run.markdown,
            validationResult=run.validation_result,
            agentActivity=run.action_history,
            errorMessage=run.error_message,
        )

    def refine(self, run_id: str, request: RefinePlanRequest) -> RefinePlanResponse | None:
        run = self.repository.get(run_id)
        if run is None or run.result is None:
            return None
        refined = self._apply_refinement(run.result, request.instruction)
        run.revision_number += 1
        run.result = refined
        run.markdown = self.markdown_renderer.render(refined)
        run.status = RunStatus.DONE
        run.message = "Plano refinado para revisao humana."
        run.updated_at = utc_now()
        run.action_history.append(
            self._action(
                run.run_id,
                "plan_refined",
                f"Instrucao aplicada: {request.instruction}",
                task_id="refine_plan_revision",
                model_profile="refinement",
                validation_result="done",
            )
        )
        self.repository.save(run)
        return RefinePlanResponse(
            runId=run.run_id,
            status=run.status,
            revisionId=new_id("rev"),
            revisionNumber=run.revision_number,
            result=refined,
            markdown=run.markdown or "",
            validationResult=ValidationResult(status="complete"),
        )

    def _apply_refinement(self, plan: OnboardingPlanResult, instruction: str) -> OnboardingPlanResult:
        data = plan.model_dump(mode="json", by_alias=True)
        data["pendingActions"].append(
            ResultItem(
                title="Ajuste solicitado pelo RH",
                ownerRole="RH",
                status=ItemStatus.PENDING,
                rationale=instruction,
            ).model_dump(mode="json", by_alias=True)
        )
        data["nextRecommendedActions"] = [
            "Revisar o ajuste solicitado antes da aprovacao.",
            *data["nextRecommendedActions"],
        ]
        data["status"] = PlanStatus.DRAFT
        return OnboardingPlanResult.model_validate(data)

    def _action(
        self,
        run_id: str,
        action_type: str,
        summary: str,
        task_id: str | None = None,
        agent_name: str | None = None,
        model_profile: str | None = None,
        validation_result: str | None = None,
    ) -> AgentAction:
        model_name = self.settings.model_profile_map().get(model_profile or "default", self.settings.llm_model)
        return AgentAction(
            runId=run_id,
            actorId=self.actor.actor_id,
            actorName=self.actor.actor_name,
            actionType=action_type,
            taskId=task_id,
            agentName=agent_name,
            status="done",
            summary=summary,
            modelProvider=self.settings.llm_provider if model_profile else None,
            modelName=model_name if model_profile else None,
            modelProfile=model_profile,
            validationResult=validation_result,
        )

    def _profile_for(self, task_id: str) -> str:
        if "it" in task_id:
            return "tool_calling"
        if "communication" in task_id or "stakeholder" in task_id:
            return "creative"
        if "document" in task_id:
            return "reasoning"
        return "default"

