from onboardflow.application.ports import CatalogPort
from onboardflow.domain.models import (
    EmployeeOnboardingInput,
    EmployeeProfile,
    ItemStatus,
    OnboardingPlanResult,
    OnboardingRun,
    PlanStatus,
    ResultItem,
    SpecialistOutput,
    ValidationResult,
)


def _item(row: dict, status: ItemStatus = ItemStatus.PENDING) -> ResultItem:
    return ResultItem(
        title=row["title"],
        ownerRole=row["owner_role"],
        status=status,
        rationale=row.get("rationale"),
    )


class DeterministicOnboardingFlow:
    """Local deterministic Flow/Crew boundary used by tests and MVP demos.

    The class preserves the approved Flow responsibility: validate and normalize structured
    outputs. Live CrewAI execution can replace the specialist generation inside this adapter
    without changing domain/application code.
    """

    def __init__(self, catalog: CatalogPort) -> None:
        self.catalog = catalog

    def execute(
        self, run: OnboardingRun, employee: EmployeeOnboardingInput, validation: ValidationResult
    ) -> tuple[list[SpecialistOutput], OnboardingPlanResult]:
        profile = EmployeeProfile(
            fullName=employee.full_name,
            role=employee.role,
            department=employee.department,
            directManager=employee.direct_manager,
            startDate=employee.start_date.isoformat(),
            workMode=employee.work_mode,
        )

        required_documents = [_item(row) for row in self.catalog.required_documents(employee)]
        it_items = [_item(row) for row in self.catalog.it_access_rules(employee)]
        training_items = [_item(row, ItemStatus.RECOMMENDED) for row in self.catalog.training_items(employee)]
        agenda_items = [
            ResultItem(
                title="Reuniao de boas-vindas com gestor",
                ownerRole="Gestor",
                status=ItemStatus.PENDING,
                rationale="Alinha expectativas e prioridades da primeira semana.",
            ),
            ResultItem(
                title="Revisao do plano com RH",
                ownerRole="RH",
                status=ItemStatus.PENDING,
                rationale="Confirma pendencias antes de qualquer comunicacao externa.",
            ),
        ]
        communications = [
            self._render_template(template, employee) for template in self.catalog.communication_templates()
        ]
        pending_actions = [
            *required_documents,
            *[item for item in it_items if item.status == ItemStatus.PENDING],
        ]
        if validation.issues:
            pending_actions.extend(
                ResultItem(
                    title=f"Resolver validacao: {issue.field}",
                    ownerRole="RH",
                    status=ItemStatus.BLOCKED if issue.severity == "error" else ItemStatus.PENDING,
                    rationale=issue.message,
                )
                for issue in validation.issues
            )

        risk_flags = [
            ResultItem(
                title="Revisao humana obrigatoria",
                ownerRole="RH",
                status=ItemStatus.RECOMMENDED,
                rationale="Comunicados e acessos sao rascunhos ate aprovacao humana.",
            )
        ]
        if employee.start_date.isoformat() <= "2026-06-07":
            risk_flags.append(
                ResultItem(
                    title="Inicio proximo",
                    ownerRole="RH",
                    status=ItemStatus.PENDING,
                    rationale="Prazo curto pode exigir priorizacao de documentos e acessos.",
                )
            )

        status = (
            PlanStatus.READY_FOR_REVIEW
            if validation.status == "complete"
            else PlanStatus.DRAFT
            if validation.status == "draft_usable"
            else PlanStatus.INCOMPLETE
        )
        plan = OnboardingPlanResult(
            employeeProfile=profile,
            executiveSummary=(
                f"Plano inicial para {employee.full_name}, {employee.role} em "
                f"{employee.department}. O conteudo esta pronto para revisao humana e nao "
                "executa envios, acessos ou provisionamentos automaticamente."
            ),
            requiredDocuments=required_documents,
            itChecklist=it_items,
            trainingPath=training_items,
            initialAgenda=agenda_items,
            communications=communications,
            pendingActions=pending_actions,
            riskFlags=risk_flags,
            status=status,
            nextRecommendedActions=[
                "Revisar pendencias antes da aprovacao do plano.",
                "Confirmar prazos de documentos e acessos com os responsaveis.",
                "Solicitar ajustes se algum item pendente bloquear a aprovacao.",
            ],
        )
        outputs = [
            self._output("validate_employee_input", "HR Intake", [], [], validation),
            self._output("generate_document_checklist", "Compliance", required_documents, [], validation),
            self._output("generate_it_checklist", "IT Provisioning", it_items, [], validation),
            self._output("generate_training_path", "Training", training_items, [], validation),
            self._output("draft_stakeholder_messages", "Communication", [], [], validation),
        ]
        return outputs, plan

    def _render_template(self, template: dict, employee: EmployeeOnboardingInput):
        from onboardflow.domain.models import CommunicationDraft

        return CommunicationDraft(
            audience=template["audience"],
            subject=template["subject"],
            body=template["body"].format(
                full_name=employee.full_name,
                direct_manager=employee.direct_manager,
                role=employee.role,
                department=employee.department,
                work_mode=employee.work_mode,
            ),
        )

    def _output(
        self,
        task_id: str,
        agent_name: str,
        items: list[ResultItem],
        risks: list[ResultItem],
        validation: ValidationResult,
    ) -> SpecialistOutput:
        return SpecialistOutput(
            taskId=task_id,
            agentName=agent_name,
            status="done" if validation.status != "unusable" else "incomplete",
            summary=f"{agent_name} output gerado com dados locais e deterministico.",
            items=items,
            risks=risks,
            assumptions=["Catalogos locais representam politicas MVP."],
            inputSources=["employee_input", "local_catalogs"],
            qualityChecks=["json_schema_valid", "human_review_required"],
        )

