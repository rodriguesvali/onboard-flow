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
    CommunicationDraft,
    DispatchChannel,
    DispatchReceipt,
    DispatchRunResponse,
    DispatchStatus,
    DispatchSummary,
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
            dispatchReceipts=run.dispatch_receipts,
            errorMessage=run.error_message,
        )

    def dispatch(self, run_id: str) -> DispatchRunResponse | None:
        run = self.repository.get(run_id)
        if run is None or run.result is None:
            return None

        existing_keys = {
            self._dispatch_key(receipt.revision_number, receipt.source_section, receipt.task_title)
            for receipt in run.dispatch_receipts
        }
        receipts: list[DispatchReceipt] = []
        already_sent = 0

        logger.info("onboarding_dispatch_started run_id=%s revision=%s", run.run_id, run.revision_number)
        for receipt in self._derive_dispatch_receipts(run, run.result):
            key = self._dispatch_key(receipt.revision_number, receipt.source_section, receipt.task_title)
            if key in existing_keys:
                already_sent += 1
                receipts.append(
                    receipt.model_copy(update={"status": DispatchStatus.ALREADY_SENT_SIMULATED})
                )
                continue

            run.dispatch_receipts.append(receipt)
            receipts.append(receipt)
            existing_keys.add(key)

        run.action_history.append(
            self._action(
                run.run_id,
                "dispatch_simulated",
                (
                    f"Envio simulado concluido: {len(receipts) - already_sent} novos recibos, "
                    f"{already_sent} ja existentes."
                ),
                task_id="dispatch_onboarding_tasks",
                agent_name="Dispatch Router",
                validation_result="sent_simulated",
            )
        )
        run.message = "Plano aprovado e envios simulados registrados."
        run.updated_at = utc_now()
        self.repository.save(run)
        logger.info(
            "onboarding_dispatch_completed run_id=%s receipts=%s already_sent=%s",
            run.run_id,
            len(receipts),
            already_sent,
        )

        return DispatchRunResponse(
            runId=run.run_id,
            revisionNumber=run.revision_number,
            status=run.status,
            dispatchSummary=self._dispatch_summary(receipts),
            receipts=receipts,
            agentActivity=run.action_history,
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

    def _derive_dispatch_receipts(
        self, run: OnboardingRun, plan: OnboardingPlanResult
    ) -> list[DispatchReceipt]:
        receipts: list[DispatchReceipt] = []

        for draft in plan.communications:
            receipts.append(self._receipt_for_communication(run, plan, draft))

        for item in plan.required_documents:
            receipts.append(self._email_receipt(run, "requiredDocuments", item.title, item.owner_role, "RH"))
        for item in plan.it_checklist:
            receipts.append(self._service_desk_receipt(run, "itChecklist", item.title, item.owner_role))
        for item in plan.training_path:
            receipts.append(
                self._receipt_for_item(run, "trainingPath", item.title, item.owner_role, default_email="Colaborador")
            )
        for item in plan.initial_agenda:
            receipts.append(self._email_receipt(run, "initialAgenda", item.title, item.owner_role, "Gestor"))
        for item in plan.pending_actions:
            receipts.append(
                self._receipt_for_item(run, "pendingActions", item.title, item.owner_role, default_email="RH")
            )
        for item in plan.risk_flags:
            receipts.append(self._email_receipt(run, "riskFlags", item.title, item.owner_role, "RH"))
        for action in plan.next_recommended_actions:
            receipts.append(self._email_receipt(run, "nextRecommendedActions", action, "RH", "RH"))

        return receipts

    def _receipt_for_communication(
        self, run: OnboardingRun, plan: OnboardingPlanResult, draft: CommunicationDraft
    ) -> DispatchReceipt:
        if draft.audience == "it":
            return self._service_desk_receipt(
                run,
                "communications",
                draft.subject,
                "TI",
                preview=draft.body,
            )
        recipient = {
            "collaborator": plan.employee_profile.full_name,
            "manager": plan.employee_profile.direct_manager,
            "hr": self.actor.actor_name,
        }.get(draft.audience, self.actor.actor_name)
        return self._email_receipt(
            run,
            "communications",
            draft.subject,
            draft.audience.upper(),
            recipient,
            preview=draft.body,
        )

    def _receipt_for_item(
        self,
        run: OnboardingRun,
        source_section: str,
        title: str,
        owner_role: str,
        default_email: str,
    ) -> DispatchReceipt:
        if owner_role.strip().lower() in {"ti", "it"}:
            return self._service_desk_receipt(run, source_section, title, owner_role)
        return self._email_receipt(run, source_section, title, owner_role, default_email)

    def _email_receipt(
        self,
        run: OnboardingRun,
        source_section: str,
        title: str,
        owner_role: str,
        recipient: str,
        preview: str | None = None,
    ) -> DispatchReceipt:
        return DispatchReceipt(
            runId=run.run_id,
            revisionNumber=run.revision_number,
            sourceSection=source_section,
            taskTitle=title,
            ownerRole=owner_role,
            channel=DispatchChannel.EMAIL,
            toolName="SimulatedEmailDispatchTool",
            recipient=recipient,
            destination=f"email::{recipient}",
            status=DispatchStatus.SENT_SIMULATED,
            payloadPreview=preview or f"Envio registrado para {recipient}: {title}",
        )

    def _service_desk_receipt(
        self,
        run: OnboardingRun,
        source_section: str,
        title: str,
        owner_role: str,
        preview: str | None = None,
    ) -> DispatchReceipt:
        ticket_key = f"SIM-{abs(hash((run.run_id, run.revision_number, source_section, title))) % 100000:05d}"
        return DispatchReceipt(
            runId=run.run_id,
            revisionNumber=run.revision_number,
            sourceSection=source_section,
            taskTitle=title,
            ownerRole=owner_role,
            channel=DispatchChannel.SERVICE_DESK,
            toolName="SimulatedServiceDeskDispatchTool",
            recipient=None,
            destination=f"service-desk::it-onboarding::{ticket_key}",
            status=DispatchStatus.SENT_SIMULATED,
            payloadPreview=preview or f"Ticket registrado {ticket_key}: {title}",
        )

    def _dispatch_key(self, revision_number: int, source_section: str, task_title: str) -> str:
        return f"{revision_number}:{source_section}:{task_title.strip().lower()}"

    def _dispatch_summary(self, receipts: list[DispatchReceipt]) -> DispatchSummary:
        return DispatchSummary(
            total=len(receipts),
            email=sum(1 for receipt in receipts if receipt.channel == DispatchChannel.EMAIL),
            serviceDesk=sum(
                1 for receipt in receipts if receipt.channel == DispatchChannel.SERVICE_DESK
            ),
            sentSimulated=sum(
                1 for receipt in receipts if receipt.status == DispatchStatus.SENT_SIMULATED
            ),
            alreadySentSimulated=sum(
                1
                for receipt in receipts
                if receipt.status == DispatchStatus.ALREADY_SENT_SIMULATED
            ),
            failedSimulated=sum(
                1 for receipt in receipts if receipt.status == DispatchStatus.FAILED_SIMULATED
            ),
        )

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
