from dataclasses import dataclass
import logging

from onboardflow.application.ports import (
    MarkdownRendererPort,
    OnboardingFlowPort,
    RunRepositoryPort,
)
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
    SpecialistOutput,
    StartRunResponse,
    ValidationIssue,
    ValidationResult,
    new_id,
    utc_now,
)

logger = logging.getLogger("uvicorn.error")


def validate_employee_input(employee: EmployeeOnboardingInput) -> ValidationResult:
    issues: list[ValidationIssue] = []
    if employee.start_date.isoformat() < "2026-01-01":
        issues.append(
            ValidationIssue(
                field="startDate",
                message="Data de inicio parece invalida.",
                severity="error",
            )
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
        logger.info(
            "onboarding_generation_started run_id=%s flow_mode=%s",
            run.run_id,
            self.settings.onboarding_flow_mode,
        )
        run.action_history.append(self._action(run.run_id, "generation_requested", "Run recebido."))
        self.repository.save(run)

        logger.info("onboarding_input_validation_started run_id=%s", run.run_id)
        validation = validate_employee_input(employee)
        logger.info(
            "onboarding_input_validation_completed run_id=%s status=%s issues=%s",
            run.run_id,
            validation.status,
            len(validation.issues),
        )
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
            logger.warning(
                "onboarding_generation_blocked run_id=%s reason=unusable_input",
                run.run_id,
            )
            run.status = RunStatus.ERROR
            run.message = "Nao foi possivel gerar o plano de onboarding."
            run.error_message = "Entrada invalida para execucao dos agentes."
            run.updated_at = utc_now()
            self.repository.save(run)
            return StartRunResponse(runId=run.run_id, status="running")

        try:
            logger.info(
                "onboarding_flow_execution_started run_id=%s flow_mode=%s",
                run.run_id,
                self.settings.onboarding_flow_mode,
            )
            specialist_outputs, plan = self.flow.execute(run, employee, validation)
        except Exception as exc:
            logger.exception(
                "onboarding_flow_execution_failed run_id=%s flow_mode=%s error=%s",
                run.run_id,
                self.settings.onboarding_flow_mode,
                exc,
            )
            run.status = RunStatus.ERROR
            run.message = "Nao foi possivel gerar o plano de onboarding."
            run.error_message = "Falha na execucao dos agentes de onboarding."
            run.updated_at = utc_now()
            run.action_history.append(
                self._action(
                    run.run_id,
                    "flow_execution_failed",
                    f"{exc.__class__.__name__}: {str(exc)[:300]}",
                    validation_result="error",
                )
            )
            self.repository.save(run)
            return StartRunResponse(runId=run.run_id, status="running")
        logger.info(
            "onboarding_flow_execution_completed run_id=%s flow_mode=%s specialist_outputs=%s",
            run.run_id,
            self.settings.onboarding_flow_mode,
            len(specialist_outputs),
        )

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
            logger.info(
                "onboarding_specialist_output_recorded run_id=%s task_id=%s agent=%s status=%s",
                run.run_id,
                output.task_id,
                output.agent_name,
                output.status,
            )

        logger.info("onboarding_plan_normalization_started run_id=%s", run.run_id)
        run.result = plan
        run.markdown = self.markdown_renderer.render(plan)
        run.status = RunStatus.DONE
        run.message = "Plano de onboarding gerado para revisao humana."
        run.updated_at = utc_now()
        run.action_history.append(
            self._action(run.run_id, "plan_normalized", "Plano JSON validado.")
        )
        self.repository.save(run)
        logger.info(
            "onboarding_generation_completed run_id=%s status=%s",
            run.run_id,
            run.status,
        )
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
        logger.info(
            "onboarding_refinement_started run_id=%s flow_mode=%s",
            run.run_id,
            self.settings.onboarding_flow_mode,
        )
        try:
            refinement_output, refined = self.flow.refine(run, run.result, request.instruction)
        except Exception as exc:
            logger.exception(
                "onboarding_refinement_flow_failed run_id=%s flow_mode=%s error=%s",
                run.run_id,
                self.settings.onboarding_flow_mode,
                exc,
            )
            run.action_history.append(
                self._action(
                    run.run_id,
                    "flow_refinement_failed",
                    f"{exc.__class__.__name__}: {str(exc)[:300]}",
                    task_id="refine_plan_revision",
                    agent_name="Refinement",
                    model_profile="refinement",
                    validation_result="error",
                )
            )
            refined = self._fallback_refinement(run.result, request.instruction)
            refinement_output = SpecialistOutput(
                taskId="refine_plan_revision",
                agentName="Refinement",
                status="incomplete",
                summary="Refinamento por Flow falhou; aplicado fallback deterministico.",
            )
            logger.info("onboarding_refinement_fallback_applied run_id=%s", run.run_id)
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
                agent_name=refinement_output.agent_name,
                model_profile="refinement",
                validation_result=refinement_output.status,
            )
        )
        self.repository.save(run)
        logger.info(
            "onboarding_refinement_completed run_id=%s revision_number=%s agent=%s status=%s",
            run.run_id,
            run.revision_number,
            refinement_output.agent_name,
            refinement_output.status,
        )
        return RefinePlanResponse(
            runId=run.run_id,
            status=run.status,
            revisionId=new_id("rev"),
            revisionNumber=run.revision_number,
            result=refined,
            markdown=run.markdown or "",
            validationResult=ValidationResult(status="complete"),
        )

    def _fallback_refinement(
        self, plan: OnboardingPlanResult, instruction: str
    ) -> OnboardingPlanResult:
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
        model_name = self.settings.model_profile_map().get(
            model_profile or "default", self.settings.llm_model
        )
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
