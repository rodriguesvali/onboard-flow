import json
import logging
import re
from contextvars import ContextVar
from importlib.resources import files
from typing import Any

from pydantic import ValidationError

from onboardflow.application.ports import CatalogPort, OnboardingFlowPort
from onboardflow.config.settings import Settings
from onboardflow.domain.models import (
    CommunicationDraft,
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

logger = logging.getLogger("uvicorn.error")

_crewai_run_id: ContextVar[str] = ContextVar("crewai_run_id", default="unknown")
_crewai_operation: ContextVar[str] = ContextVar("crewai_operation", default="unknown")
_crewai_logging_listener: object | None = None


def _item(row: dict, status: ItemStatus = ItemStatus.PENDING) -> ResultItem:
    return ResultItem(
        title=row["title"],
        ownerRole=row["owner_role"],
        status=status,
        rationale=row.get("rationale"),
    )


def _log_agent_started(flow_mode: str, run_id: str, task_id: str, agent_name: str) -> None:
    logger.info(
        "agent_operation_started flow_mode=%s run_id=%s task_id=%s agent=%s",
        flow_mode,
        run_id,
        task_id,
        agent_name,
    )


def _log_agent_completed(
    flow_mode: str,
    run_id: str,
    task_id: str,
    agent_name: str,
    status: str,
    summary: str,
) -> None:
    logger.info(
        "agent_operation_completed flow_mode=%s run_id=%s task_id=%s agent=%s status=%s summary=%s",
        flow_mode,
        run_id,
        task_id,
        agent_name,
        status,
        summary,
    )


def _log_agent_failed(
    flow_mode: str,
    run_id: str,
    task_id: str,
    agent_name: str,
    error: str,
) -> None:
    logger.exception(
        "agent_operation_failed flow_mode=%s run_id=%s task_id=%s agent=%s error=%s",
        flow_mode,
        run_id,
        task_id,
        agent_name,
        error,
    )


def _ensure_crewai_logging_listener() -> None:
    global _crewai_logging_listener

    if _crewai_logging_listener is not None:
        return

    try:
        from crewai.events import BaseEventListener
        from crewai.events.types.agent_events import (
            AgentExecutionCompletedEvent,
            AgentExecutionErrorEvent,
            AgentExecutionStartedEvent,
        )
        from crewai.events.types.crew_events import (
            CrewKickoffCompletedEvent,
            CrewKickoffFailedEvent,
            CrewKickoffStartedEvent,
        )
        from crewai.events.types.task_events import (
            TaskCompletedEvent,
            TaskFailedEvent,
            TaskStartedEvent,
        )
    except ImportError as exc:
        logger.warning("crewai_event_listener_unavailable error=%s", exc)
        return

    class CrewAILoggingEventListener(BaseEventListener):
        def setup_listeners(self, crewai_event_bus):
            @crewai_event_bus.on(CrewKickoffStartedEvent)
            def on_crew_started(source, event):
                logger.info(
                    "crewai_crew_started run_id=%s operation=%s crew=%s",
                    _crewai_run_id.get(),
                    _crewai_operation.get(),
                    _event_attr(event, "crew_name"),
                )

            @crewai_event_bus.on(CrewKickoffCompletedEvent)
            def on_crew_completed(source, event):
                logger.info(
                    "crewai_crew_completed run_id=%s operation=%s crew=%s",
                    _crewai_run_id.get(),
                    _crewai_operation.get(),
                    _event_attr(event, "crew_name"),
                )

            @crewai_event_bus.on(CrewKickoffFailedEvent)
            def on_crew_failed(source, event):
                logger.error(
                    "crewai_crew_failed run_id=%s operation=%s crew=%s error=%s",
                    _crewai_run_id.get(),
                    _crewai_operation.get(),
                    _event_attr(event, "crew_name"),
                    _event_error(event),
                )

            @crewai_event_bus.on(TaskStartedEvent)
            def on_task_started(source, event):
                logger.info(
                    "crewai_task_started run_id=%s operation=%s task=%s",
                    _crewai_run_id.get(),
                    _crewai_operation.get(),
                    _event_task(event),
                )

            @crewai_event_bus.on(TaskCompletedEvent)
            def on_task_completed(source, event):
                logger.info(
                    "crewai_task_completed run_id=%s operation=%s task=%s",
                    _crewai_run_id.get(),
                    _crewai_operation.get(),
                    _event_task(event),
                )

            @crewai_event_bus.on(TaskFailedEvent)
            def on_task_failed(source, event):
                logger.error(
                    "crewai_task_failed run_id=%s operation=%s task=%s error=%s",
                    _crewai_run_id.get(),
                    _crewai_operation.get(),
                    _event_task(event),
                    _event_error(event),
                )

            @crewai_event_bus.on(AgentExecutionStartedEvent)
            def on_agent_started(source, event):
                logger.info(
                    "crewai_agent_started run_id=%s operation=%s agent=%s task=%s",
                    _crewai_run_id.get(),
                    _crewai_operation.get(),
                    _event_agent(event),
                    _event_task(event),
                )

            @crewai_event_bus.on(AgentExecutionCompletedEvent)
            def on_agent_completed(source, event):
                logger.info(
                    "crewai_agent_completed run_id=%s operation=%s agent=%s task=%s",
                    _crewai_run_id.get(),
                    _crewai_operation.get(),
                    _event_agent(event),
                    _event_task(event),
                )

            @crewai_event_bus.on(AgentExecutionErrorEvent)
            def on_agent_failed(source, event):
                logger.error(
                    "crewai_agent_failed run_id=%s operation=%s agent=%s task=%s error=%s",
                    _crewai_run_id.get(),
                    _crewai_operation.get(),
                    _event_agent(event),
                    _event_task(event),
                    _event_error(event),
                )

    _crewai_logging_listener = CrewAILoggingEventListener()


def _event_attr(event: object, name: str) -> str:
    value = getattr(event, name, None)
    return str(value) if value is not None else "unknown"


def _event_agent(event: object) -> str:
    agent = getattr(event, "agent", None)
    role = getattr(agent, "role", None)
    if role:
        return str(role)
    return _event_attr(event, "agent_role")


def _event_task(event: object) -> str:
    task = getattr(event, "task", None)
    description = getattr(task, "description", None)
    if description:
        return str(description).splitlines()[0][:160]
    return _event_attr(event, "task_id")


def _event_error(event: object) -> str:
    error = getattr(event, "error", None) or getattr(event, "exception", None)
    return str(error)[:500] if error is not None else "unknown"


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

        _log_agent_started(
            "deterministic", run.run_id, "generate_document_checklist", "Compliance"
        )
        try:
            required_documents = [_item(row) for row in self.catalog.required_documents(employee)]
        except Exception as exc:
            _log_agent_failed(
                "deterministic",
                run.run_id,
                "generate_document_checklist",
                "Compliance",
                str(exc),
            )
            raise
        _log_agent_completed(
            "deterministic",
            run.run_id,
            "generate_document_checklist",
            "Compliance",
            "done",
            f"{len(required_documents)} documento(s) obrigatorio(s) identificado(s).",
        )

        _log_agent_started("deterministic", run.run_id, "generate_it_checklist", "IT Provisioning")
        try:
            it_items = [_item(row) for row in self.catalog.it_access_rules(employee)]
        except Exception as exc:
            _log_agent_failed(
                "deterministic",
                run.run_id,
                "generate_it_checklist",
                "IT Provisioning",
                str(exc),
            )
            raise
        _log_agent_completed(
            "deterministic",
            run.run_id,
            "generate_it_checklist",
            "IT Provisioning",
            "done",
            f"{len(it_items)} item(ns) de TI identificado(s).",
        )

        _log_agent_started("deterministic", run.run_id, "generate_training_path", "Training")
        try:
            training_items = [
                _item(row, ItemStatus.RECOMMENDED) for row in self.catalog.training_items(employee)
            ]
        except Exception as exc:
            _log_agent_failed(
                "deterministic",
                run.run_id,
                "generate_training_path",
                "Training",
                str(exc),
            )
            raise
        _log_agent_completed(
            "deterministic",
            run.run_id,
            "generate_training_path",
            "Training",
            "done",
            f"{len(training_items)} item(ns) de treinamento identificado(s).",
        )
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
        _log_agent_started(
            "deterministic", run.run_id, "draft_stakeholder_messages", "Communication"
        )
        try:
            communications = [
                self._render_template(template, employee)
                for template in self.catalog.communication_templates()
            ]
        except Exception as exc:
            _log_agent_failed(
                "deterministic",
                run.run_id,
                "draft_stakeholder_messages",
                "Communication",
                str(exc),
            )
            raise
        _log_agent_completed(
            "deterministic",
            run.run_id,
            "draft_stakeholder_messages",
            "Communication",
            "done",
            f"{len(communications)} comunicado(s) em rascunho preparado(s).",
        )
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
            self._output(
                "generate_document_checklist", "Compliance", required_documents, [], validation
            ),
            self._output("generate_it_checklist", "IT Provisioning", it_items, [], validation),
            self._output("generate_training_path", "Training", training_items, [], validation),
            self._output("draft_stakeholder_messages", "Communication", [], [], validation),
        ]
        return outputs, plan

    def refine(
        self, run: OnboardingRun, current_plan: OnboardingPlanResult, instruction: str
    ) -> tuple[SpecialistOutput, OnboardingPlanResult]:
        _log_agent_started("deterministic", run.run_id, "refine_plan_revision", "Refinement")
        try:
            refined = _apply_refinement(current_plan, instruction)
        except Exception as exc:
            _log_agent_failed(
                "deterministic",
                run.run_id,
                "refine_plan_revision",
                "Refinement",
                str(exc),
            )
            raise
        _log_agent_completed(
            "deterministic",
            run.run_id,
            "refine_plan_revision",
            "Refinement",
            "done",
            "Plano refinado com regra deterministica local.",
        )
        output = SpecialistOutput(
            taskId="refine_plan_revision",
            agentName="Refinement",
            status="done",
            summary="Plano refinado com regra deterministica local.",
            pendingActions=[
                ResultItem(
                    title="Ajuste solicitado pelo RH",
                    ownerRole="RH",
                    status=ItemStatus.PENDING,
                    rationale=instruction,
                )
            ],
            assumptions=["Refinamento deterministico preserva o contrato do MVP."],
            inputSources=["current_plan", "refinement_instruction"],
            qualityChecks=["json_schema_valid", "human_review_required"],
        )
        return output, refined

    def _render_template(
        self, template: dict, employee: EmployeeOnboardingInput
    ) -> CommunicationDraft:
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


class LiveCrewAIOnboardingFlow:
    """CrewAI-backed specialist execution with Flow-level normalization.

    The Crew may enrich specialist analysis, but final plan shaping remains here so the
    API contract, human-review boundary, and catalog-backed safeguards stay deterministic.
    """

    TASK_ORDER = [
        "validate_employee_input",
        "generate_document_checklist",
        "generate_it_checklist",
        "generate_training_path",
        "draft_stakeholder_messages",
    ]
    AGENT_BY_TASK = {
        "validate_employee_input": "hr_intake_agent",
        "generate_document_checklist": "compliance_agent",
        "generate_it_checklist": "it_provisioning_agent",
        "generate_training_path": "training_agent",
        "draft_stakeholder_messages": "communication_agent",
    }
    PROFILE_BY_AGENT = {
        "hr_intake_agent": "default",
        "compliance_agent": "reasoning",
        "it_provisioning_agent": "tool_calling",
        "training_agent": "efficient",
        "communication_agent": "creative",
        "refinement_agent": "refinement",
    }
    AGENT_DISPLAY_NAMES = {
        "hr_intake_agent": "HR Intake",
        "compliance_agent": "Compliance",
        "it_provisioning_agent": "IT Provisioning",
        "training_agent": "Training",
        "communication_agent": "Communication",
        "refinement_agent": "Refinement",
    }

    def __init__(self, catalog: CatalogPort, settings: Settings) -> None:
        self.catalog = catalog
        self.settings = settings
        self._deterministic = DeterministicOnboardingFlow(catalog)
        self.agents_config = self._load_yaml("agents.yaml")
        self.tasks_config = self._load_yaml("tasks.yaml")

    def execute(
        self, run: OnboardingRun, employee: EmployeeOnboardingInput, validation: ValidationResult
    ) -> tuple[list[SpecialistOutput], OnboardingPlanResult]:
        _ensure_crewai_logging_listener()
        crewai = self._import_crewai()
        agents = self._build_agents(crewai)
        tasks = self._build_tasks(crewai, agents)
        crew = crewai["Crew"](
            agents=list(agents.values()),
            tasks=list(tasks.values()),
            process=crewai["Process"].sequential,
            verbose=self.settings.crewai_verbose,
        )
        run_token = _crewai_run_id.set(run.run_id)
        operation_token = _crewai_operation.set("generation")
        try:
            crew.kickoff(inputs=self._crew_inputs(run, employee, validation))
        finally:
            _crewai_operation.reset(operation_token)
            _crewai_run_id.reset(run_token)
        outputs = [self._read_task_output(task_id, tasks[task_id]) for task_id in self.TASK_ORDER]
        return outputs, self._normalize_plan(employee, validation, outputs)

    def refine(
        self, run: OnboardingRun, current_plan: OnboardingPlanResult, instruction: str
    ) -> tuple[SpecialistOutput, OnboardingPlanResult]:
        _ensure_crewai_logging_listener()
        crewai = self._import_crewai()
        agents = self._build_agents(crewai)
        task = self._build_refinement_task(crewai, agents["refinement_agent"])
        crew = crewai["Crew"](
            agents=[agents["refinement_agent"]],
            tasks=[task],
            process=crewai["Process"].sequential,
            verbose=self.settings.crewai_verbose,
        )
        run_token = _crewai_run_id.set(run.run_id)
        operation_token = _crewai_operation.set("refinement")
        try:
            crew.kickoff(inputs=self._refinement_inputs(run, current_plan, instruction))
        finally:
            _crewai_operation.reset(operation_token)
            _crewai_run_id.reset(run_token)
        refined_plan = self._read_plan_output(task)
        output_status = "done"
        summary = "Plano refinado por agente CrewAI e validado pelo Flow."
        if refined_plan is None:
            refined_plan = _apply_refinement(current_plan, instruction)
            output_status = "incomplete"
            summary = "Saida do agente de refinamento invalida; aplicado fallback deterministico."
        refined_plan = self._normalize_refined_plan(current_plan, refined_plan, instruction)
        output = SpecialistOutput(
            taskId="refine_plan_revision",
            agentName=self.AGENT_DISPLAY_NAMES["refinement_agent"],
            status=output_status,
            summary=summary,
            pendingActions=[
                ResultItem(
                    title="Ajuste solicitado pelo RH",
                    ownerRole="RH",
                    status=ItemStatus.PENDING,
                    rationale=instruction,
                )
            ],
            inputSources=["current_plan", "refinement_instruction", "crewai"],
            qualityChecks=["json_schema_valid", "human_review_required"],
        )
        return output, refined_plan

    def _import_crewai(self) -> dict[str, Any]:
        try:
            from crewai import Agent, Crew, LLM, Process, Task
        except ImportError as exc:
            raise RuntimeError(
                "CrewAI execution requested but CrewAI is not installed. "
                "Run `uv sync --all-extras --dev` in backend/."
            ) from exc
        return {"Agent": Agent, "Crew": Crew, "LLM": LLM, "Process": Process, "Task": Task}

    def _build_agents(self, crewai: dict[str, Any]) -> dict[str, Any]:
        agents = {}
        for agent_id, config in self.agents_config.items():
            profile = self.PROFILE_BY_AGENT.get(agent_id, "default")
            llm = crewai["LLM"](
                model=self.settings.crewai_model_name(profile),
                temperature=self.settings.crewai_temperature,
            )
            agents[agent_id] = crewai["Agent"](
                config=config,
                llm=llm,
                allow_delegation=False,
                verbose=self.settings.crewai_verbose,
            )
        return agents

    def _build_tasks(self, crewai: dict[str, Any], agents: dict[str, Any]) -> dict[str, Any]:
        tasks = {}
        for task_id in self.TASK_ORDER:
            config = dict(self.tasks_config[task_id])
            agent_id = self.AGENT_BY_TASK[task_id]
            config["description"] = self._task_description(task_id, config["description"])
            config["expected_output"] = self._expected_output(task_id)
            context_ids = config.pop("context", []) or []
            tasks[task_id] = crewai["Task"](
                config=config,
                agent=agents[agent_id],
                context=[tasks[context_id] for context_id in context_ids],
                output_json=SpecialistOutput,
            )
        return tasks

    def _build_refinement_task(self, crewai: dict[str, Any], agent: Any) -> Any:
        config = dict(self.tasks_config["refine_onboarding_plan"])
        config["description"] = (
            config["description"]
            + "\n\nCurrent plan JSON: {current_plan_json}\n"
            + "Refinement instruction: {refinement_instruction}\n"
            + "Return a complete OnboardingPlanResult JSON object. Preserve the employee profile "
            + "and do not claim that messages were sent, access was provisioned, systems were "
            + "changed, or a plan was approved. Set status to draft unless the instruction only "
            + "clarifies copy without changing review state."
        )
        config["expected_output"] = (
            "A complete JSON object matching OnboardingPlanResult: employeeProfile, "
            "executiveSummary, requiredDocuments, itChecklist, trainingPath, initialAgenda, "
            "communications, pendingActions, riskFlags, status, and nextRecommendedActions."
        )
        return crewai["Task"](
            config=config,
            agent=agent,
            output_json=OnboardingPlanResult,
        )

    def _task_description(self, task_id: str, base: str) -> str:
        return (
            f"{base}\n\n"
            f"Task id: {task_id}. Return only validated structured JSON. "
            "Do not claim that emails were sent, access was provisioned, systems were changed, "
            "or a plan was approved. All output is advisory and pending human review.\n"
            "Employee input JSON: {employee_json}\n"
            "Validation JSON: {validation_json}\n"
            "Local catalog JSON: {catalog_json}\n"
            "Use the local catalog as the source of truth for mandatory documents, access, "
            "equipment, and training rules. If uncertain, add assumptions or risks instead of "
            "inventing completed actions."
        )

    def _expected_output(self, task_id: str) -> str:
        communication_note = ""
        if task_id == "draft_stakeholder_messages":
            communication_note = (
                " Include communication drafts in communications when useful. "
                "Each draft must have audience, subject, body, and draft=true."
            )
        return (
            "A JSON object matching SpecialistOutput: taskId, agentName, status, summary, "
            "items, pendingActions, risks, communications, assumptions, inputSources, "
            "and qualityChecks. status must be done or incomplete."
            f"{communication_note}"
        )

    def _crew_inputs(
        self, run: OnboardingRun, employee: EmployeeOnboardingInput, validation: ValidationResult
    ) -> dict[str, str]:
        catalog = {
            "requiredDocuments": self.catalog.required_documents(employee),
            "itAccessRules": self.catalog.it_access_rules(employee),
            "trainingItems": self.catalog.training_items(employee),
            "communicationTemplates": self.catalog.communication_templates(),
        }
        return {
            "run_id": run.run_id,
            "employee_json": employee.model_dump_json(by_alias=True),
            "validation_json": validation.model_dump_json(by_alias=True),
            "catalog_json": json.dumps(catalog, ensure_ascii=True),
        }

    def _refinement_inputs(
        self, run: OnboardingRun, current_plan: OnboardingPlanResult, instruction: str
    ) -> dict[str, str]:
        return {
            "run_id": run.run_id,
            "current_plan_json": current_plan.model_dump_json(by_alias=True),
            "refinement_instruction": instruction,
        }

    def _read_task_output(self, task_id: str, task: Any) -> SpecialistOutput:
        task_output = getattr(task, "output", None)
        agent_id = self.AGENT_BY_TASK[task_id]
        agent_name = self.AGENT_DISPLAY_NAMES[agent_id]
        if task_output is None:
            return self._fallback_output(task_id, agent_name, "CrewAI task did not expose output.")

        pydantic_output = getattr(task_output, "pydantic", None)
        if isinstance(pydantic_output, SpecialistOutput):
            return pydantic_output
        if pydantic_output is not None:
            try:
                return SpecialistOutput.model_validate(pydantic_output)
            except ValidationError:
                pass

        json_dict = getattr(task_output, "json_dict", None)
        if json_dict:
            try:
                return SpecialistOutput.model_validate(json_dict)
            except ValidationError:
                pass

        raw = getattr(task_output, "raw", "") or str(task_output)
        try:
            return SpecialistOutput.model_validate(json.loads(self._extract_json(raw)))
        except (json.JSONDecodeError, ValidationError, TypeError):
            return self._fallback_output(task_id, agent_name, raw[:500])

    def _read_plan_output(self, task: Any) -> OnboardingPlanResult | None:
        task_output = getattr(task, "output", None)
        if task_output is None:
            return None

        pydantic_output = getattr(task_output, "pydantic", None)
        if isinstance(pydantic_output, OnboardingPlanResult):
            return pydantic_output
        if pydantic_output is not None:
            try:
                return OnboardingPlanResult.model_validate(pydantic_output)
            except ValidationError:
                pass

        json_dict = getattr(task_output, "json_dict", None)
        if json_dict:
            try:
                return OnboardingPlanResult.model_validate(json_dict)
            except ValidationError:
                pass

        raw = getattr(task_output, "raw", "") or str(task_output)
        try:
            return OnboardingPlanResult.model_validate(json.loads(self._extract_json(raw)))
        except (json.JSONDecodeError, ValidationError, TypeError):
            return None

    def _extract_json(self, raw: str) -> str:
        stripped = raw.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL)
        if match:
            return match.group(1)
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if match:
            return match.group(0)
        return stripped

    def _fallback_output(self, task_id: str, agent_name: str, summary: str) -> SpecialistOutput:
        return SpecialistOutput(
            taskId=task_id,
            agentName=agent_name,
            status="incomplete",
            summary=summary or "CrewAI task output could not be parsed.",
            assumptions=["CrewAI output required Flow-level fallback normalization."],
            inputSources=["employee_input", "local_catalogs", "crewai"],
            qualityChecks=["output_parse_failed", "human_review_required"],
        )

    def _normalize_plan(
        self,
        employee: EmployeeOnboardingInput,
        validation: ValidationResult,
        outputs: list[SpecialistOutput],
    ) -> OnboardingPlanResult:
        _, baseline = self._deterministic.execute(OnboardingRun(), employee, validation)
        by_task = {output.task_id: output for output in outputs}
        # Catalog-derived sections remain deterministic. CrewAI may enrich analysis,
        # but it must not move requirements across document, IT, and training sections.
        required_documents = baseline.required_documents
        it_items = baseline.it_checklist
        training_items = baseline.training_path
        communication_output = by_task.get("draft_stakeholder_messages")
        communications = (
            communication_output.communications
            if communication_output and communication_output.communications
            else baseline.communications
        )
        risks = self._merge_items(baseline.risk_flags, *(output.risks for output in outputs))
        pending_actions = self._merge_items(
            [item for item in required_documents if item.status != ItemStatus.DONE],
            [item for item in it_items if item.status == ItemStatus.PENDING],
            *(output.pending_actions for output in outputs),
        )
        incomplete_outputs = [
            output.agent_name for output in outputs if output.status == "incomplete"
        ]
        if incomplete_outputs:
            risks = self._merge_items(
                risks,
                [
                    ResultItem(
                        title="Saida de agente incompleta",
                        ownerRole="RH",
                        status=ItemStatus.RECOMMENDED,
                        rationale="Revisar agentes: " + ", ".join(incomplete_outputs),
                    )
                ],
            )
        status = baseline.status if not incomplete_outputs else PlanStatus.DRAFT
        summaries = [output.summary for output in outputs if output.summary]
        executive_summary = (
            f"Plano inicial para {employee.full_name}, {employee.role} em {employee.department}. "
            "Especialistas CrewAI executaram analise consultiva com normalizacao pelo Flow. "
            "Nenhum envio, acesso, provisionamento ou aprovacao externa foi executado."
        )
        if summaries:
            executive_summary += " Resumos: " + " | ".join(summaries[:3])
        return OnboardingPlanResult(
            employeeProfile=baseline.employee_profile,
            executiveSummary=executive_summary,
            requiredDocuments=required_documents,
            itChecklist=it_items,
            trainingPath=training_items,
            initialAgenda=baseline.initial_agenda,
            communications=communications,
            pendingActions=pending_actions,
            riskFlags=risks,
            status=status,
            nextRecommendedActions=baseline.next_recommended_actions,
        )

    def _normalize_refined_plan(
        self,
        current_plan: OnboardingPlanResult,
        refined_plan: OnboardingPlanResult,
        instruction: str,
    ) -> OnboardingPlanResult:
        data = refined_plan.model_dump(mode="json", by_alias=True)
        data["employeeProfile"] = current_plan.employee_profile.model_dump(
            mode="json", by_alias=True
        )
        data["status"] = PlanStatus.DRAFT
        data["pendingActions"] = self._merge_items(
            [
                ResultItem.model_validate(item)
                for item in data.get("pendingActions", [])
            ],
            [
                ResultItem(
                    title="Ajuste solicitado pelo RH",
                    ownerRole="RH",
                    status=ItemStatus.PENDING,
                    rationale=instruction,
                )
            ],
        )
        data["pendingActions"] = [
            item.model_dump(mode="json", by_alias=True) for item in data["pendingActions"]
        ]
        next_actions = list(data.get("nextRecommendedActions", []))
        review_action = "Revisar a versao refinada antes da aprovacao."
        if review_action not in next_actions:
            next_actions = [review_action, *next_actions]
        data["nextRecommendedActions"] = next_actions
        return OnboardingPlanResult.model_validate(data)

    def _merge_items(self, *groups: list[ResultItem]) -> list[ResultItem]:
        merged: list[ResultItem] = []
        seen: set[tuple[str, str]] = set()
        for group in groups:
            for item in group:
                key = (item.title.lower(), item.owner_role.lower())
                if key not in seen:
                    seen.add(key)
                    merged.append(item)
        return merged

    def _load_yaml(self, name: str) -> dict[str, Any]:
        import yaml

        resource = files("onboardflow.crews.onboarding_analysis_crew.config").joinpath(name)
        return yaml.safe_load(resource.read_text(encoding="utf-8"))


def build_onboarding_flow(catalog: CatalogPort, settings: Settings) -> OnboardingFlowPort:
    if settings.onboarding_flow_mode == "crewai":
        return LiveCrewAIOnboardingFlow(catalog, settings)
    return DeterministicOnboardingFlow(catalog)


def _apply_refinement(
    plan: OnboardingPlanResult, instruction: str
) -> OnboardingPlanResult:
    data = plan.model_dump(mode="json", by_alias=True)
    adjustment = ResultItem(
        title="Ajuste solicitado pelo RH",
        ownerRole="RH",
        status=ItemStatus.PENDING,
        rationale=instruction,
    )
    data["executiveSummary"] = (
        f"{data['executiveSummary']} Ajustes solicitados pelo RH foram incorporados "
        "como nova versao de rascunho para revisao humana."
    )
    data["pendingActions"].append(adjustment.model_dump(mode="json", by_alias=True))
    for section_name, item in _section_adjustments(instruction).items():
        data[section_name].append(item.model_dump(mode="json", by_alias=True))
    data["nextRecommendedActions"] = [
        "Revisar a nova versao ajustada antes da aprovacao.",
        *data["nextRecommendedActions"],
    ]
    data["status"] = PlanStatus.DRAFT
    return OnboardingPlanResult.model_validate(data)


def _section_adjustments(instruction: str) -> dict[str, ResultItem]:
    normalized = instruction.lower()
    adjustments: dict[str, ResultItem] = {}
    if any(token in normalized for token in ["agenda", "prazo", "prazos", "reuniao", "reunião"]):
        adjustments["initialAgenda"] = ResultItem(
            title="Revisao da agenda inicial solicitada",
            ownerRole="RH",
            status=ItemStatus.PENDING,
            rationale=instruction,
        )
    if any(token in normalized for token in ["documento", "documentacao", "documentação"]):
        adjustments["requiredDocuments"] = ResultItem(
            title="Revisao de documentos solicitada",
            ownerRole="RH",
            status=ItemStatus.PENDING,
            rationale=instruction,
        )
    if any(
        token in normalized
        for token in ["it", "ti", "acesso", "acessos", "equipamento", "notebook", "vpn"]
    ):
        adjustments["itChecklist"] = ResultItem(
            title="Revisao de acessos e equipamentos solicitada",
            ownerRole="IT",
            status=ItemStatus.PENDING,
            rationale=instruction,
        )
    if any(token in normalized for token in ["treinamento", "treinamentos", "trilha", "curso"]):
        adjustments["trainingPath"] = ResultItem(
            title="Revisao da trilha de treinamento solicitada",
            ownerRole="Treinamento",
            status=ItemStatus.RECOMMENDED,
            rationale=instruction,
        )
    if any(token in normalized for token in ["risco", "riscos", "bloqueio", "bloqueios"]):
        adjustments["riskFlags"] = ResultItem(
            title="Revisao de riscos solicitada",
            ownerRole="RH",
            status=ItemStatus.RECOMMENDED,
            rationale=instruction,
        )
    if not adjustments:
        adjustments["pendingActions"] = ResultItem(
            title="Revisao geral solicitada",
            ownerRole="RH",
            status=ItemStatus.PENDING,
            rationale=instruction,
        )
    return adjustments
